package com.sqi.auth;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * This class handles profile operations.
 * The class annotation below sets the API base path.
 */
@RestController
@RequestMapping("/api/profile")
public class DocController {
    // A commented-out mapping that should be ignored:
    // @GetMapping("/ghost")
    // public String ghost() { return "ghost"; }

    private String base = "http://example.com";

    @GetMapping("/me")
    public String me() {
        return "me";
    }

    @GetMapping("/proxy")
    public String proxy() {
        return base;
    }
}
