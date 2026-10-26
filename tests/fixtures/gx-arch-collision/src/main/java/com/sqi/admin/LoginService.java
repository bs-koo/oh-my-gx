package com.sqi.admin;

import org.springframework.stereotype.Service;

@Service
public class LoginService {
    public String authenticate(String adminId) {
        return adminId;
    }
}
