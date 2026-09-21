package com.sqi.generated;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class GeneratedController {
    @GetMapping("/api/generated")
    public String generated() {
        return "generated";
    }
}
