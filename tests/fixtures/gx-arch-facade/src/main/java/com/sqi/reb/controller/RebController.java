package com.sqi.reb.controller;

@RestController
@RequestMapping("/api/reb")
public class RebController {
    private final RebFacade rebFacade;
    private final ExcelSupport excelSupport;

    @GetMapping("/list")
    public String list() {
        return rebFacade.list();
    }
}
