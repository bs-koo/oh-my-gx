package shop.service;
@Service
public class OrderService {
    private final OrderMapper mapper;
    public String list() { return mapper.archive(); }
}
