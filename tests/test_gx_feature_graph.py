"""실제 배포 JS의 기능별 관계 투영 계약을 Node 내장 런타임으로 확인한다."""
import json
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / '.claude/skills/gx-visualize/templates/feature-graph.js'
NODE = shutil.which('node')
RUNNER = r'''
const fs = require('node:fs');
const vm = require('node:vm');
vm.runInThisContext(fs.readFileSync(process.argv[1], 'utf8'));
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
const before = JSON.stringify(input);
const result = globalThis.GXFeatureGraph.project(input.nodes, input.edges, input.startId, input.includeDependencies);
process.stdout.write(JSON.stringify({result, unchanged: before === JSON.stringify(input)}));
'''


def node(identifier, kind='service', **extra):
    return {'id': identifier, 'kind': kind, **extra}


def edge(identifier, source, target, relation='calls'):
    return {'id': identifier, 'source': source, 'target': target, 'relation': relation}


class FeatureGraphTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not NODE:
            raise unittest.SkipTest('Node is required to execute the deployed JavaScript')

    def project(self, nodes, edges, start='api-a', dependencies=False):
        result = subprocess.run([NODE, '-e', RUNNER, str(SCRIPT)],
                                input=json.dumps({'nodes': nodes, 'edges': edges, 'startId': start,
                                                  'includeDependencies': dependencies}),
                                text=True, encoding='utf-8', capture_output=True, timeout=10, check=True)
        payload = json.loads(result.stdout)
        self.assertTrue(payload['unchanged'], 'projection must not mutate the shared IR')
        return payload['result']

    def test_confirmed_relations_follow_direction_and_include_descendants(self):
        nodes = [node('api-a', 'api'), node('screen', 'screen'), node('svc'), node('repo', 'repository'), node('table', 'table')]
        edges = [edge('incoming', 'screen', 'api-a', 'requests'), edge('call', 'api-a', 'svc'),
                 edge('delegate', 'svc', 'repo'), edge('read', 'repo', 'table', 'reads'),
                 edge('write', 'repo', 'table', 'writes')]
        result = self.project(nodes, edges)
        self.assertEqual(['api-a', 'repo', 'svc', 'table'], result['nodeIds'])
        self.assertEqual(['call', 'delegate', 'read', 'write'], result['edgeIds'])
        self.assertEqual(result['nodeIds'], result['directNodeIds'])
        self.assertEqual([], result['dependencyNodeIds'])

    def test_dependencies_are_opt_in_and_their_descendants_remain_candidates(self):
        nodes = [node('api-a', 'api'), node('svc'), node('optional'), node('repo', 'repository'), node('table', 'table')]
        edges = [edge('call', 'api-a', 'svc'), edge('injected', 'svc', 'optional', 'depends_on'),
                 edge('lookup', 'optional', 'repo'), edge('read', 'repo', 'table', 'reads')]
        default = self.project(nodes, edges)
        self.assertEqual(['api-a', 'svc'], default['nodeIds'])
        expanded = self.project(nodes, edges, dependencies=True)
        self.assertEqual(['api-a', 'optional', 'repo', 'svc', 'table'], expanded['nodeIds'])
        self.assertEqual(['optional', 'repo', 'table'], expanded['dependencyNodeIds'])
        self.assertEqual(['api-a', 'svc'], expanded['directNodeIds'])
        self.assertEqual(['call', 'injected', 'lookup', 'read'], expanded['edgeIds'])

    def test_confirmed_path_takes_precedence_when_candidate_paths_rejoin(self):
        nodes = [node('api-a', 'api'), node('candidate'), node('shared'), node('table', 'table')]
        edges = [edge('direct', 'api-a', 'shared'), edge('dependency', 'api-a', 'candidate', 'depends_on'),
                 edge('join', 'candidate', 'shared'), edge('read', 'shared', 'table', 'reads')]
        result = self.project(nodes, edges, dependencies=True)
        self.assertEqual(['candidate'], result['dependencyNodeIds'])
        self.assertEqual(['api-a', 'shared', 'table'], result['directNodeIds'])
        self.assertIn('join', result['edgeIds'])

    def test_shared_table_does_not_pull_in_other_api_or_its_service(self):
        nodes = [node('api-a', 'api'), node('api-b', 'api'), node('svc-a'), node('svc-b'), node('table', 'table')]
        edges = [edge('a', 'api-a', 'svc-a'), edge('b', 'api-b', 'svc-b'),
                 edge('read-a', 'svc-a', 'table', 'reads'), edge('read-b', 'svc-b', 'table', 'reads'),
                 edge('out-of-table', 'table', 'svc-b')]
        result = self.project(nodes, edges)
        self.assertEqual(['api-a', 'svc-a', 'table'], result['nodeIds'])
        self.assertEqual(['a', 'read-a'], result['edgeIds'])

    def test_other_api_and_screen_are_not_traversed_even_by_calls(self):
        nodes = [node('api-a', 'api'), node('svc'), node('api-b', 'api'), node('screen-b', 'screen'), node('hidden')]
        edges = [edge('a', 'api-a', 'svc'), edge('b', 'svc', 'api-b'), edge('screen', 'svc', 'screen-b', 'requests'),
                 edge('hidden', 'api-b', 'hidden')]
        result = self.project(nodes, edges, dependencies=True)
        self.assertEqual(['api-a', 'svc'], result['nodeIds'])
        self.assertEqual(['a'], result['edgeIds'])

    def test_external_node_is_a_boundary_even_when_local_edges_exist(self):
        nodes = [node('api-a', 'api'), node('external', external_domain='billing'), node('hidden')]
        edges = [edge('call', 'api-a', 'external'), edge('boundary-leak', 'external', 'hidden')]
        result = self.project(nodes, edges)
        self.assertEqual(['api-a', 'external'], result['nodeIds'])
        self.assertEqual(['call'], result['edgeIds'])
        external_start = self.project(nodes, edges, start='external', dependencies=True)
        self.assertEqual(['external'], external_start['nodeIds'])
        self.assertEqual([], external_start['edgeIds'])

    def test_cycles_terminate_and_keep_only_reachable_edges(self):
        nodes = [node('api-a', 'api'), node('a'), node('b'), node('unrelated')]
        edges = [edge('start', 'api-a', 'a'), edge('forward', 'a', 'b'), edge('back', 'b', 'a'),
                 edge('self', 'b', 'b'), edge('unrelated', 'unrelated', 'unrelated')]
        result = self.project(nodes, edges)
        self.assertEqual(['a', 'api-a', 'b'], result['nodeIds'])
        self.assertEqual(['back', 'forward', 'self', 'start'], result['edgeIds'])

    def test_missing_start_and_isolated_api_have_explicit_empty_or_single_results(self):
        nodes = [node('api-a', 'api')]
        empty = self.project(nodes, [], start='missing')
        self.assertEqual({'nodeIds': [], 'edgeIds': [], 'directNodeIds': [], 'dependencyNodeIds': []}, empty)
        isolated = self.project(nodes, [])
        self.assertEqual(['api-a'], isolated['nodeIds'])
        self.assertEqual(['api-a'], isolated['directNodeIds'])
        self.assertEqual([], isolated['edgeIds'])

    def test_unknown_relations_dangling_edges_and_edges_without_ids_are_ignored(self):
        nodes = [node('api-a', 'api'), node('hidden')]
        edges = [edge('unknown', 'api-a', 'hidden', 'contains'), edge('dangling', 'api-a', 'missing'),
                 edge('missing-source', 'missing', 'hidden'), {'source': 'api-a', 'target': 'hidden', 'relation': 'calls'},
                 edge('', 'api-a', 'hidden'), None]
        result = self.project(nodes, edges, dependencies=True)
        self.assertEqual(['api-a'], result['nodeIds'])
        self.assertEqual([], result['edgeIds'])

    def test_screen_start_follows_non_entry_request_targets(self):
        nodes = [node('screen', 'screen'), node('svc')]
        result = self.project(nodes, [edge('request', 'screen', 'svc', 'requests')], start='screen')
        self.assertEqual(['screen', 'svc'], result['nodeIds'])
        self.assertEqual(['request'], result['edgeIds'])

    def test_screen_allows_only_its_direct_request_apis(self):
        nodes = [node('screen', 'screen'), node('api-a', 'api'), node('api-b', 'api'), node('api-other', 'api'),
                 node('svc'), node('candidate'), node('screen-other', 'screen')]
        edges = [edge('request-a', 'screen', 'api-a', 'requests'), edge('request-b', 'screen', 'api-b', 'requests'),
                 edge('call-a', 'api-a', 'svc'), edge('call-b', 'api-b', 'svc'),
                 edge('indirect-api', 'svc', 'api-other', 'requests'), edge('wrong-relation', 'screen', 'api-other'),
                 edge('other-screen', 'screen', 'screen-other', 'requests'),
                 edge('dependency', 'screen', 'candidate', 'depends_on'), edge('candidate-api', 'candidate', 'api-other', 'requests')]
        result = self.project(nodes, edges, start='screen', dependencies=True)
        self.assertEqual(['api-a', 'api-b', 'candidate', 'screen', 'svc'], result['nodeIds'])
        self.assertEqual(['call-a', 'call-b', 'dependency', 'request-a', 'request-b'], result['edgeIds'])
        self.assertEqual(['candidate'], result['dependencyNodeIds'])

    def test_order_is_stable_when_ir_input_order_changes(self):
        nodes = [node('api-a', 'api'), node('한글'), node('z'), node('a')]
        edges = [edge('z', 'api-a', '한글'), edge('a', '한글', 'z'), edge('가', 'z', 'a')]
        first = self.project(nodes, edges)
        second = self.project(list(reversed(nodes)), list(reversed(edges)))
        self.assertEqual(first, second)
        self.assertEqual(['a', 'api-a', 'z', '한글'], first['nodeIds'])


if __name__ == '__main__':
    unittest.main()
