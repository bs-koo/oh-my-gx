package com.sqi.auth;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/tight")
public class TightController {
    @GetMapping("/first")
    public String first() {
        return "first";
    }
}
