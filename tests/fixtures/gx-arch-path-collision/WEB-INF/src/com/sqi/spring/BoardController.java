package com.sqi.spring;

import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class BoardController {
    @PostMapping("/board/list.do")
    public String list() {
        return "ok";
    }
}
