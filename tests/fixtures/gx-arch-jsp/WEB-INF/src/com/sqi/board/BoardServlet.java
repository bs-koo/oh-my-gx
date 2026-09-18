package com.sqi.board;

import javax.servlet.http.HttpServlet;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

public class BoardServlet extends HttpServlet {
    private final BoardDAO boardDAO = new BoardDAO();

    protected void doPost(HttpServletRequest request, HttpServletResponse response) {
        boardDAO.selectList();
    }
}
