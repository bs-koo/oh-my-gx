"""구조 맵이 추측한 호출·테이블을 사실처럼 표시하지 않도록 검증한다."""
import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / ".claude/skills/gx-visualize/scripts/scan_entrypoints.py"
spec = importlib.util.spec_from_file_location("scan_accuracy", SCRIPT)
scanner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scanner)


class ScanAccuracyTests(unittest.TestCase):
    def scan(self, files):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name, content in files.items():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
            return scanner.scan(root)

    def pairs(self, result):
        labels = {node["id"]: node["label"] for node in result["nodes"]}
        return {(labels[e["source"]], e["relation"], labels[e["target"]]) for e in result["edges"]}

    def test_endpoint_calls_are_scoped_to_method_and_ignore_comments_and_strings(self):
        result = self.scan({
            "StatusController.java": '''@RestController class StatusController {
              private final UserService users;
              private final AuditService audit;
              @GetMapping("/health") public String health() { return "users.find()"; }
              @GetMapping("/users") public Object list() {
                // audit.record();
                return this.users.find();
              }
            }''',
            "UserService.java": "@Service class UserService {}",
            "AuditService.java": "@Service class AuditService {}",
        })
        self.assertEqual({("StatusController.list", "calls", "UserService")}, self.pairs(result))
        self.assertEqual(7, result["edges"][0]["evidence"][0]["line"])
        self.assertEqual("static-call", result["edges"][0]["analysis"])

    def test_unused_service_field_is_dependency_and_primitives_are_excluded(self):
        result = self.scan({
            "OrderService.java": '''@Service class OrderService {
                final StoreDAO store;
                protected String message;
                private int count;
            }''',
            "StoreDAO.java": "class StoreDAO {}",
        })
        self.assertEqual({("OrderService", "depends_on", "StoreDAO")}, self.pairs(result))
        self.assertEqual([], result["unresolved_edges"])

    def test_service_shadowed_parameter_keeps_only_type_dependency(self):
        result = self.scan({
            "OrderService.java": '''@Service class OrderService {
                final StoreDAO store;
                public Object find(OtherDAO store) { return store.find(); }
            }''',
            "StoreDAO.java": "class StoreDAO {}",
        })
        self.assertEqual({("OrderService", "depends_on", "StoreDAO")}, self.pairs(result))
        self.assertEqual("ambiguous-call-receiver", result["diagnostics"][0]["code"])

    def test_interface_throws_clause_is_not_a_field_dependency(self):
        result = self.scan({"OrderService.java": '''@Service interface OrderService {
            Object find() throws IOException;
            Object create() throws java.io.IOException;
        }'''})
        self.assertEqual([], result["edges"])
        self.assertEqual([], result["unresolved_edges"])

    def test_other_objects_field_is_not_a_current_class_field_call(self):
        result = self.scan({
            "OrderService.java": '''@Service class OrderService {
                BillingService billing;
                void run(Other other) { other.billing.charge(); other . /* receiver */ billing.charge(); }
            }''',
            "BillingService.java": "@Service class BillingService {}",
        })
        self.assertEqual({("OrderService", "depends_on", "BillingService")}, self.pairs(result))

    def test_current_class_explicit_this_and_bare_receivers_remain_calls(self):
        for receiver in ("this.billing", "billing"):
            with self.subTest(receiver=receiver):
                result = self.scan({
                    "OrderService.java": "@Service class OrderService { BillingService billing; void run() { " + receiver + ".charge(); } }",
                    "BillingService.java": "@Service class BillingService {}",
                })
                self.assertEqual({("OrderService", "calls", "BillingService")}, self.pairs(result))

    def test_array_multiline_noarg_and_explicit_http_methods(self):
        result = self.scan({"RouteController.java": '''@RestController
            @RequestMapping(path = {"/v1", "/v2"})
            class RouteController {
                @GetMapping(path = {
                    "/a", "/b"
                })
                public String list() { return ""; }
                @PostMapping
                public String create() { return ""; }
                @RequestMapping(value="/route", method={RequestMethod.PUT, RequestMethod.PATCH})
                public String route() { return ""; }
            }'''})
        by_name = {node["symbol"]: node for node in result["nodes"]}
        self.assertEqual(["GET /v1/a", "GET /v1/b", "GET /v2/a", "GET /v2/b"], by_name["RouteController.list"]["routes"])
        self.assertEqual(["POST /v1", "POST /v2"], by_name["RouteController.create"]["routes"])
        self.assertEqual(4, len(by_name["RouteController.route"]["routes"]))

    def test_class_http_methods_combine_with_method_as_spring_union(self):
        result = self.scan({"RouteController.java": '''@RestController
            @RequestMapping(path="/api", method=RequestMethod.GET)
            class RouteController {
                @RequestMapping("/items") public Object items() { return null; }
                @PostMapping("/create") public Object create() { return null; }
            }'''})
        routes = {node["symbol"]: node["routes"] for node in result["nodes"]}
        self.assertEqual(["GET /api/items"], routes["RouteController.items"])
        self.assertEqual(["GET /api/create", "POST /api/create"], routes["RouteController.create"])

    def test_dynamic_mapping_is_diagnostic_not_a_guessed_literal(self):
        result = self.scan({"RouteController.java": '''@RestController class RouteController {
            @GetMapping(BASE + "/item") public String list() { return ""; }
        }'''})
        self.assertEqual([], result["nodes"])
        self.assertEqual("unsupported-mapping", result["diagnostics"][0]["code"])
        self.assertEqual("RouteController.java", result["diagnostics"][0]["file"])

    def test_dynamic_class_prefix_does_not_emit_incomplete_endpoint_paths(self):
        result = self.scan({"RouteController.java": '''@RestController @RequestMapping(BASE)
            class RouteController { @GetMapping("/item") public String list() { return ""; } }'''})
        self.assertEqual([], result["nodes"])
        self.assertEqual("unsupported-mapping", result["diagnostics"][0]["code"])

    def test_shadowed_receiver_is_not_assigned_to_injected_field(self):
        result = self.scan({
            "RouteController.java": '''@RestController class RouteController {
                private UserService users;
                @GetMapping("/other") public Object list(OtherService users) { return users.find(); }
                @GetMapping("/real") public Object real(OtherService users) { return this.users.find(); }
            }''',
            "UserService.java": "@Service class UserService {}",
        })
        self.assertEqual({("RouteController.real", "calls", "UserService")}, self.pairs(result))
        self.assertEqual("ambiguous-call-receiver", result["diagnostics"][0]["code"])

    def test_declared_unique_interface_merges_non_impl_name(self):
        result = self.scan({
            "Search.java": "public interface Search { String query(); }",
            "ElasticSearch.java": "@Service class ElasticSearch implements Search { final SearchDAO dao; public String query() { return dao.query(); } }",
            "SearchDAO.java": "class SearchDAO {}",
        })
        self.assertEqual({("Search", "calls", "SearchDAO")}, self.pairs(result))
        node = next(node for node in result["nodes"] if node["label"] == "Search")
        self.assertEqual(2, len(node["evidence"]))

    def test_multiple_implementations_are_not_collapsed(self):
        result = self.scan({
            "Search.java": "public interface Search {}",
            "First.java": "@Service class First implements Search {}",
            "Second.java": "@Service class Second implements Search {}",
        })
        self.assertEqual({"Search", "First", "Second"}, {node["label"] for node in result["nodes"]})

    def test_service_component_reader_connects_merged_service_to_mapper_and_table(self):
        result = self.scan({
            "service/OrderService.java": "public interface OrderService { Object read(); }",
            "service/impl/OrderServiceImpl.java": '''@Service class OrderServiceImpl implements OrderService {
                private final OrderReader reader;
                public Object read() { return reader.read(); }
            }''',
            "service/impl/OrderReader.java": '''@Component @RequiredArgsConstructor class OrderReader {
                private final OrderMapper mapper;
                public Object read() { return mapper.find(); }
            }''',
            "mapper/OrderMapper.java": "@Mapper interface OrderMapper { Object find(); }",
            "mapper/OrderMapper.xml": '<mapper namespace="OrderMapper"><select id="find">SELECT * FROM orders</select></mapper>',
        })
        self.assertEqual({("OrderService", "calls", "OrderReader"), ("OrderReader", "calls", "OrderMapper"),
                          ("OrderMapper", "reads", "ORDERS")}, self.pairs(result))
        self.assertEqual([], result["unresolved_edges"])
        reader_edge = next(edge for edge in result["edges"] if edge["source"].endswith("--OrderReader"))
        self.assertEqual("service/impl/OrderReader.java", reader_edge["evidence"][0]["file"])
        self.assertEqual(3, reader_edge["evidence"][0]["line"])

    def test_service_package_component_is_supported_without_service_directory(self):
        result = self.scan({"QueryReader.java": "package app.orders.service.impl; @Component class QueryReader {}"})
        self.assertEqual([("QueryReader", "service")], [(node["label"], node["kind"]) for node in result["nodes"]])

    def test_component_outside_service_and_unannotated_helper_stay_excluded(self):
        result = self.scan({
            "support/ExcelSupport.java": "package app.support; @Component class ExcelSupport {}",
            "service/PlainReader.java": "package app.service; class PlainReader {}",
            "services/OtherReader.java": "package app.services; @Component class OtherReader {}",
            "service/ScanConfig.java": "package app.service; @ComponentScan class ScanConfig {}",
        })
        self.assertEqual([], result["nodes"])

    def test_component_service_layer_dao_keeps_repository_priority(self):
        result = self.scan({
            "service/OrderDao.java": "@Component class OrderDao {}",
            "OrderDAO.java": "package app.order.service; @Component class OrderDAO {}",
        })
        self.assertEqual({("OrderDao", "repository"), ("OrderDAO", "repository")},
                         {(node["label"], node["kind"]) for node in result["nodes"]})

    def test_sql_comments_literals_cte_functions_and_schema_identity(self):
        tables = scanner._sql_tables('''
            WITH recent AS (SELECT * FROM app.real_table), another(id) AS (SELECT id FROM second)
            SELECT 'FROM fake_table', x.id FROM recent x
            JOIN another y ON x.id=y.id
            JOIN generate_series(1, 5) g ON 1=1
            -- FROM commented
            /* JOIN hidden */
            JOIN other.real_table t ON t.id=x.id
        ''')
        self.assertEqual([("APP.REAL_TABLE", "reads"), ("OTHER.REAL_TABLE", "reads"), ("SECOND", "reads")], tables)

    def test_insert_select_distinguishes_read_and_write(self):
        self.assertEqual([("APP.DEST", "writes"), ("APP.SOURCE", "reads")], scanner._sql_tables("INSERT INTO app.dest(id) SELECT id FROM app.source"))

    def test_update_from_and_delete_using_distinguish_targets(self):
        self.assertEqual([("DEST", "writes"), ("SOURCE", "reads")], scanner._sql_tables("UPDATE dest SET id=s.id FROM source s WHERE dest.id=s.id"))
        self.assertEqual([("DEST", "writes"), ("SOURCE", "reads")], scanner._sql_tables("DELETE FROM dest USING source WHERE dest.id=source.id"))

    def test_only_comma_join_and_table_functions(self):
        self.assertEqual([("ONE", "reads"), ("TWO", "reads")], scanner._sql_tables("SELECT * FROM ONLY one a, two b, LATERAL unnest(a.ids) x"))

    def test_merge_reads_source_and_upsert_does_not_write_a_column_table(self):
        self.assertEqual([("DEST", "writes"), ("SOURCE", "reads")], scanner._sql_tables("MERGE INTO dest USING source ON dest.id=source.id WHEN MATCHED THEN UPDATE SET value=1"))
        self.assertEqual([("DEST", "writes")], scanner._sql_tables("INSERT INTO dest(id) VALUES(1) ON DUPLICATE KEY UPDATE id=1"))

    def test_qualified_dynamic_table_is_not_a_schema_table(self):
        self.assertEqual([], scanner._sql_tables("SELECT * FROM app.${table}"))

    def test_from_inside_scalar_function_is_not_a_table_clause(self):
        for expression in ("EXTRACT(YEAR FROM created_at)", "SUBSTRING(name FROM offset_column)", "TRIM(BOTH 'x' FROM name)"):
            with self.subTest(expression=expression):
                self.assertEqual([("ORDERS", "reads")], scanner._sql_tables("SELECT " + expression + " FROM orders"))

    def test_subquery_inside_scalar_function_keeps_its_from_table(self):
        self.assertEqual([("ORDERS", "reads"), ("RATES", "reads")], scanner._sql_tables(
            "SELECT COALESCE((SELECT MAX(rate) FROM rates), 1), EXTRACT(YEAR FROM created_at) FROM orders"))

    def test_distinct_from_comparison_does_not_create_column_or_keyword_tables(self):
        self.assertEqual([("ORDERS", "reads")], scanner._sql_tables(
            "SELECT * FROM orders WHERE name IS DISTINCT FROM 'INPUT' AND status IS NOT DISTINCT FROM other.status ORDER BY id"))
        self.assertEqual([("ORDERS", "writes")], scanner._sql_tables(
            "INSERT INTO orders(id) VALUES(1) ON CONFLICT(id) DO UPDATE SET name=EXCLUDED.name WHERE orders.name IS DISTINCT FROM EXCLUDED.name"))

    def test_xml_include_expands_and_preserves_fragment_evidence(self):
        result = self.scan({
            "StoreDAO.java": "class StoreDAO {}",
            "common.xml": '<mapper namespace="common">\n<sql id="source"> FROM app.inventory </sql></mapper>',
            "StoreMapper.xml": '''<mapper namespace="StoreDAO">
                <!-- <select id="fake">SELECT * FROM fake</select> -->
                <select id="list">SELECT * <include refid="common.source"/><where><if test="active">active=1</if></where></select>
            </mapper>''',
        })
        self.assertEqual({("StoreDAO", "reads", "INVENTORY")}, self.pairs(result))
        table = next(node for node in result["nodes"] if node["kind"] == "table")
        self.assertEqual("gx-table--APP.INVENTORY", table["id"])
        self.assertEqual({"StoreMapper.xml", "common.xml"}, {item["file"] for item in table["evidence"]})

    def test_include_child_properties_resolve_table_and_alias(self):
        result = self.scan({
            "StoreDAO.java": "class StoreDAO {}",
            "StoreMapper.xml": '''<mapper namespace="StoreDAO">
                <sql id="table"> FROM ${table} ${alias} </sql>
                <select id="list">SELECT * <include refid="table">
                    <property name="table" value="app.orders"/><property name="alias" value="o"/>
                </include></select>
            </mapper>''',
        })
        self.assertEqual({("StoreDAO", "reads", "ORDERS")}, self.pairs(result))
        self.assertEqual([], result["diagnostics"])

    def test_nested_include_inherits_shadows_and_does_not_leak_properties(self):
        result = self.scan({
            "StoreDAO.java": "class StoreDAO {}",
            "StoreMapper.xml": '''<mapper namespace="StoreDAO">
                <sql id="source"> SELECT * FROM ${table} </sql>
                <sql id="pair">
                    <include refid="${fragment}"><property name="table" value="app.inner"/></include>
                    UNION ALL <include refid="source"/>
                </sql>
                <select id="list"><include refid="pair">
                    <property name="table" value="app.outer"/><property name="fragment" value="source"/>
                </include></select>
            </mapper>''',
        })
        self.assertEqual({("StoreDAO", "reads", "INNER"), ("StoreDAO", "reads", "OUTER")}, self.pairs(result))
        self.assertEqual([], result["diagnostics"])

    def test_external_fragment_unqualified_include_uses_calling_namespace(self):
        result = self.scan({
            "StoreDAO.java": "class StoreDAO {}",
            "common.xml": '<mapper namespace="common"><sql id="wrapper"><include refid="source"/></sql><sql id="source"> FROM wrong_table </sql></mapper>',
            "StoreMapper.xml": '<mapper namespace="StoreDAO"><sql id="source"> FROM right_table </sql><select id="list">SELECT * <include refid="common.wrapper"/></select></mapper>',
        })
        self.assertEqual({("StoreDAO", "reads", "RIGHT_TABLE")}, self.pairs(result))

    def test_include_duplicate_properties_are_diagnosed_without_expansion(self):
        result = self.scan({"StoreMapper.xml": '''<mapper namespace="StoreDAO">
            <sql id="source">FROM ${table}</sql>
            <select id="list">SELECT * <include refid="source"><property name="table" value="first"/><property name="table" value="second"/></include></select>
        </mapper>'''})
        self.assertEqual([], result["nodes"])
        self.assertIn("duplicate-sql-include-property", {item["code"] for item in result["diagnostics"]})

    def test_same_include_properties_do_not_resolve_each_other_or_refid(self):
        result = self.scan({"StoreMapper.xml": '''<mapper namespace="StoreDAO">
            <sql id="source">FROM ${table}</sql>
            <select id="list">SELECT * <include refid="source"><property name="schema" value="app"/><property name="table" value="${schema}.orders"/></include></select>
            <select id="other">SELECT * <include refid="${fragment}"><property name="fragment" value="source"/></include></select>
        </mapper>'''})
        self.assertEqual([], result["nodes"])
        codes = {item["code"] for item in result["diagnostics"]}
        self.assertIn("dynamic-sql-identifier", codes)
        self.assertIn("unresolved-sql-include", codes)

    def test_cdata_include_text_and_xml_comments_are_not_executed(self):
        result = self.scan({
            "StoreDAO.java": "class StoreDAO {}",
            "StoreMapper.xml": '''<mapper namespace="StoreDAO">
                <sql id="wrong"> FROM false_table </sql>
                <sql id="real"><![CDATA[SELECT '<include refid="wrong"/>' FROM ${table}]]></sql>
                <!-- <select id="ignored"><include refid="wrong"/></select> -->
                <select id="list"><include refid="real"><property name="table" value="orders"/></include></select>
            </mapper>''',
        })
        self.assertEqual({("StoreDAO", "reads", "ORDERS")}, self.pairs(result))
        self.assertEqual([], result["diagnostics"])

    def test_cdata_sql_like_xml_does_not_define_statements_or_fragments(self):
        result = self.scan({
            "StoreDAO.java": "class StoreDAO {}",
            "StoreMapper.xml": '''<mapper namespace="StoreDAO">
                <sql id="real"><![CDATA[SELECT '<select id="fake">FROM false_table</select>' FROM orders]]></sql>
                <select id="list"><include refid="real"/></select>
            </mapper>''',
        })
        self.assertEqual({("StoreDAO", "reads", "ORDERS")}, self.pairs(result))
        self.assertEqual([], result["diagnostics"])

    def test_include_xml_entities_are_decoded_and_malformed_xml_is_diagnosed(self):
        result = self.scan({
            "StoreDAO.java": "class StoreDAO {}",
            "StoreMapper.xml": '''<mapper namespace="StoreDAO">
                <sql id="source">FROM ${table}</sql>
                <select id="valid">SELECT * <include refid="source"><property name="table" value="app.&#111;rders"/></include></select>
                <select id="invalid">SELECT * <include refid="source"><property name="table" value="bad"/></select>
            </mapper>''',
        })
        self.assertEqual({("StoreDAO", "reads", "ORDERS")}, self.pairs(result))
        self.assertIn("unsupported-sql-xml", {item["code"] for item in result["diagnostics"]})

    def test_include_expansion_fanout_has_a_diagnostic_budget(self):
        fragments = ['<sql id="f0">FROM orders</sql>']
        for depth in range(1, 11):
            fragments.append(f'<sql id="f{depth}"><include refid="f{depth - 1}"/><include refid="f{depth - 1}"/></sql>')
        result = self.scan({"StoreMapper.xml": '<mapper namespace="StoreDAO">' + ''.join(fragments) + '<select id="list">SELECT * <include refid="f10"/></select></mapper>'})
        self.assertIn("sql-include-limit", {item["code"] for item in result["diagnostics"]})

    def test_dynamic_where_and_if_keep_sql_token_boundaries(self):
        result = self.scan({
            "StoreDAO.java": "class StoreDAO {}",
            "StoreMapper.xml": '''<mapper namespace="StoreDAO"><select id="list">
                SELECT * FROM orders<if test="expanded">JOIN customers ON orders.customer_id=customers.id</if><where>id=#{id}</where>
            </select></mapper>''',
        })
        self.assertEqual({("StoreDAO", "reads", "ORDERS"), ("StoreDAO", "reads", "CUSTOMERS")}, self.pairs(result))

    def test_choose_table_identifier_stays_unresolved_instead_of_concatenating(self):
        result = self.scan({
            "StoreDAO.java": "class StoreDAO {}",
            "StoreMapper.xml": '''<mapper namespace="StoreDAO"><select id="list">
                SELECT * FROM <choose><when test="active">orders</when><otherwise>archived_orders</otherwise></choose>
            </select></mapper>''',
        })
        self.assertEqual([], [node for node in result["nodes"] if node["kind"] == "table"])
        self.assertIn("dynamic-sql-branch", {item["code"] for item in result["diagnostics"]})

    def test_choose_queries_are_diagnosed_without_selecting_a_branch(self):
        result = self.scan({"StoreMapper.xml": '''<mapper namespace="StoreDAO"><select id="list">
            <choose><when test="active">SELECT * FROM orders</when><otherwise>SELECT * FROM archived_orders</otherwise></choose>
        </select></mapper>'''})
        self.assertEqual([], result["nodes"])
        self.assertIn("dynamic-sql-branch", {item["code"] for item in result["diagnostics"]})

    def test_foreach_and_where_preserve_outer_table_without_guessing_loop_sql(self):
        result = self.scan({
            "StoreDAO.java": "class StoreDAO {}",
            "StoreMapper.xml": '''<mapper namespace="StoreDAO"><select id="list">
                SELECT * FROM orders<where>id IN <foreach collection="ids" item="id" open="(" close=")" separator=",">#{id}</foreach></where>
            </select><select id="dynamic">SELECT * FROM <foreach collection="tables" item="table" separator=",">${table}</foreach></select></mapper>''',
        })
        self.assertEqual({("StoreDAO", "reads", "ORDERS")}, self.pairs(result))
        self.assertIn("dynamic-sql-loop", {item["code"] for item in result["diagnostics"]})

    def test_cyclic_include_and_unsupported_children_are_diagnosed(self):
        result = self.scan({"StoreMapper.xml": '''<mapper namespace="StoreDAO">
            <sql id="cycle"><include refid="cycle"/></sql>
            <sql id="source">FROM orders</sql>
            <select id="list"><include refid="cycle"/></select>
            <select id="other"><include refid="source"><if test="bad"/></include></select>
        </mapper>'''})
        self.assertEqual([], result["nodes"])
        self.assertEqual({"unresolved-sql-include", "unsupported-sql-include"}, {item["code"] for item in result["diagnostics"]})

    def test_unresolved_include_and_dynamic_sql_have_actionable_diagnostics(self):
        result = self.scan({"StoreMapper.xml": '''<mapper namespace="StoreDAO">
            <select id="list">SELECT * FROM ${table} <include refid="missing"/></select>
        </mapper>'''})
        self.assertEqual([], result["nodes"])
        self.assertEqual({"unresolved-sql-include", "dynamic-sql-identifier"}, {item["code"] for item in result["diagnostics"]})
        self.assertTrue(all(item["file"] == "StoreMapper.xml" and item["line"] == 2 for item in result["diagnostics"]))

    def test_excluded_directories_are_not_scanned(self):
        result = self.scan({"node_modules/FakeService.java": "@Service class FakeService {}", "RealService.java": "@Service class RealService {}"})
        self.assertEqual(["RealService"], [node["label"] for node in result["nodes"]])

    def test_harness_worktree_copies_are_excluded_from_project_scan(self):
        result = self.scan({
            "RealService.java": "@Service class RealService {}",
            ".claude/worktrees/branch/RealService.java": "@Service class RealService {}",
            ".codex/worktrees/branch/RealService.java": "@Service class RealService {}",
        })
        self.assertEqual(["RealService"], [node["label"] for node in result["nodes"]])
        self.assertEqual(["RealService.java"], list(result["files"]))


if __name__ == "__main__":
    unittest.main()
