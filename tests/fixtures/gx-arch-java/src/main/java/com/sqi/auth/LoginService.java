package com.sqi.auth;

import org.springframework.stereotype.Service;

@Service
public class LoginService {
    private final LoginMapper loginMapper;

    public LoginService(LoginMapper loginMapper) {
        this.loginMapper = loginMapper;
    }

    public String authenticate(String userId) {
        return loginMapper.selectUser(userId);
    }
}
