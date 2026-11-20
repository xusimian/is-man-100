package com.xusimian.isman100

import android.app.Activity
import android.content.Context
import android.os.Bundle
import android.view.View
import android.view.WindowManager
import android.view.inputmethod.EditorInfo
import android.view.inputmethod.InputMethodManager
import android.widget.EditText
import com.xusimian.isman100.ui.GameView

/**
 * 应用入口 —— 对应 Python 版 mac/main.py。
 *
 * 全屏沉浸式，隐藏状态栏/导航栏，锁定竖屏。
 */
class MainActivity : Activity() {

    private lateinit var gameView: GameView

    /**
     * 名字输入用的隐藏 EditText。
     *
     * ⚠️ 不能用 setContentView 替换整个视图（那会把 GameView 踢出屏幕），
     *    必须作为 GameView 的子 View 加进去，用 GONE 隐藏但保留 IME 焦点。
     */
    private lateinit var nameInput: EditText

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // 全屏沉浸
        window.setFlags(
            WindowManager.LayoutParams.FLAG_FULLSCREEN,
            WindowManager.LayoutParams.FLAG_FULLSCREEN
        )
        hideSystemUi()

        gameView = GameView(this)
        gameView.nameInputCallback = object : GameView.NameInputCallback {
            override fun onRequestKeyboard() = showNameKeyboard()
            override fun onHideKeyboard() = hideNameKeyboard()
        }

        // 根布局：GameView + 隐藏的输入框（承载名字输入）
        val root = android.widget.FrameLayout(this)
        root.addView(
            gameView,
            android.widget.FrameLayout.LayoutParams(
                android.widget.FrameLayout.LayoutParams.MATCH_PARENT,
                android.widget.FrameLayout.LayoutParams.MATCH_PARENT
            )
        )

        // 隐藏的输入框：承载名字输入（中文 IME）
        nameInput = EditText(this).apply {
            setSingleLine()
            visibility = View.GONE
            inputType = android.text.InputType.TYPE_CLASS_TEXT
            imeOptions = EditorInfo.IME_ACTION_DONE
            setBackgroundColor(android.graphics.Color.TRANSPARENT)
        }
        root.addView(
            nameInput,
            android.widget.FrameLayout.LayoutParams(1, 1)
        )
        setContentView(root)

        nameInput.setOnEditorActionListener { _, _, _ ->
            // 回车确认
            gameView.submitCurrentName()
            true
        }
        nameInput.addTextChangedListener(object : android.text.TextWatcher {
            override fun beforeTextChanged(s: CharSequence?, a: Int, b: Int, c: Int) {}
            override fun onTextChanged(s: CharSequence?, a: Int, b: Int, c: Int) {}
            override fun afterTextChanged(s: android.text.Editable?) {
                onNameTextChanged(s?.toString() ?: "")
            }
        })
    }

    override fun onWindowFocusChanged(hasFocus: Boolean) {
        super.onWindowFocusChanged(hasFocus)
        if (hasFocus) {
            hideSystemUi()
        }
    }

    private fun hideSystemUi() {
        @Suppress("DEPRECATION")
        window.decorView.systemUiVisibility = (
            View.SYSTEM_UI_FLAG_LAYOUT_STABLE
                or View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION
                or View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
                or View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
                or View.SYSTEM_UI_FLAG_FULLSCREEN
                or View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
            )
    }

    /**
     * 显示软键盘并把输入转发给 GameView。
     */
    fun showNameKeyboard() {
        nameInput.setText("")
        nameInput.requestFocus()
        val imm = getSystemService(Context.INPUT_METHOD_SERVICE) as InputMethodManager
        imm.showSoftInput(nameInput, InputMethodManager.SHOW_IMPLICIT)
    }

    /**
     * 隐藏软键盘。
     */
    fun hideNameKeyboard() {
        val imm = getSystemService(Context.INPUT_METHOD_SERVICE) as InputMethodManager
        imm.hideSoftInputFromWindow(nameInput.windowToken, 0)
        nameInput.clearFocus()
    }

    /**
     * 名字输入变化时同步给 GameView。
     */
    fun onNameTextChanged(text: String) {
        gameView.setNameInput(text)
    }
}
