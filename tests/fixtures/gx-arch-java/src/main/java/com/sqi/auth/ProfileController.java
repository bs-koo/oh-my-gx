package com.sqi.auth;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/profile")
public class ProfileController {
    @Autowired
    private LoginService loginService;

    @GetMapping("/me")
    public String me(String userId) {
        return loginService.authenticate(userId);
    }
}
