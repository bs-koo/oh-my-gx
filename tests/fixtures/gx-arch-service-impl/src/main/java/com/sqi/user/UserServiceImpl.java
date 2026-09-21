package com.sqi.user;

import org.springframework.stereotype.Service;

@Service
public class UserServiceImpl implements UserService {
    private final UserMapper userMapper;

    public UserServiceImpl(UserMapper userMapper) {
        this.userMapper = userMapper;
    }

    @Override
    public String authenticate(String userId) {
        return userMapper.selectUser(userId);
    }
}
