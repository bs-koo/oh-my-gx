package com.sqi.admin;

import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class AdminController {
    private final LoginService loginService;

    public AdminController(LoginService loginService) {
        this.loginService = loginService;
    }

    @PostMapping("/api/admin/login")
    public String login(String adminId) {
        return loginService.authenticate(adminId);
    }
}
