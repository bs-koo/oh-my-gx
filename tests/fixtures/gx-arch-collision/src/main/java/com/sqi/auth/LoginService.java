package com.sqi.auth;

import org.springframework.stereotype.Service;

@Service
public class LoginService {
    public String authenticate(String userId) {
        return userId;
    }
}
