package com.sqi.auth;

import org.apache.ibatis.annotations.Mapper;

@Mapper
public interface LoginMapper {
    String selectUser(String userId);
}
