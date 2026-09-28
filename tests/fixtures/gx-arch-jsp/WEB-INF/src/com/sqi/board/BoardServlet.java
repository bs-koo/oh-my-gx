package com.sqi.board;

import javax.servlet.annotation.WebServlet;
import javax.servlet.http.HttpServlet;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

@WebServlet("/board/list.do")
public class BoardServlet extends HttpServlet {
    private final BoardDAO boardDAO = new BoardDAO();

    protected void doPost(HttpServletRequest request, HttpServletResponse response) {
        boardDAO.selectList();
    }
}
