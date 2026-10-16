package shop.controller;
@RestController
@RequestMapping("/api")
public class OrderController {
    private final OrderService orders;
    private final BillingService billing;
    @GetMapping("/health")
    public String health() { return "ok"; }
    @GetMapping(path = {"/orders", "/purchases"})
    public String list() { return orders.list(); }
    @PostMapping("/checkout")
    public String checkout() { return billing.charge(); }
}
