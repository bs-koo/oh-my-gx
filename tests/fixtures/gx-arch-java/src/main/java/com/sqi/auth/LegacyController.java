package com.sqi.auth;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestMethod;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class LegacyController {
    @RequestMapping(value = "/legacy/ping", method = RequestMethod.GET)
    public String ping() {
        return "pong";
    }

    @GetMapping("/a")
    public String methodA() {
        return "a";
    }

    @RequestMapping(value = "/b", method = RequestMethod.POST)
    public String methodB() {
        return "b";
    }
}
