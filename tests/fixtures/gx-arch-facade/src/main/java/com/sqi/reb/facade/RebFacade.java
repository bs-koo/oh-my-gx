package com.sqi.reb.facade;

@Component
public class RebFacade {
    private final RebService rebService;

    public String list() {
        return rebService.list();
    }
}
