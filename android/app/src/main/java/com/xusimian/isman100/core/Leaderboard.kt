package com.xusimian.isman100.core

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/**
 * 高分榜 —— 对应 Python 版 core/leaderboard.py。
 *
 * Android 上用 SharedPreferences 存储（应用沙盒内，无需权限）。
 */
class Leaderboard(context: Context) {

    data class Entry(
        val name: String,
        val time: Float,
        val date: String
    )

    private val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
    private val entries = mutableListOf<Entry>()

    init {
        load()
    }

    /** 从存储加载榜单 */
    private fun load() {
        entries.clear()
        try {
            val raw = prefs.getString(KEY_ENTRIES, null) ?: return
            val array = JSONArray(raw)
            for (i in 0 until minOf(array.length(), MAX_ENTRIES)) {
                val obj = array.getJSONObject(i)
                entries.add(
                    Entry(
                        name = obj.optString("name", "匿名"),
                        time = obj.optDouble("time", 0.0).toFloat(),
                        date = obj.optString("date", "")
                    )
                )
            }
        } catch (e: Exception) {
            // 存档损坏时静默降级为空榜，不影响游戏
            entries.clear()
        }
    }

    /** 保存榜单 */
    private fun save() {
        try {
            val array = JSONArray()
            for (e in entries.take(MAX_ENTRIES)) {
                array.put(
                    JSONObject()
                        .put("name", e.name)
                        .put("time", e.time.toDouble())
                        .put("date", e.date)
                )
            }
            prefs.edit().putString(KEY_ENTRIES, array.toString()).apply()
        } catch (e: Exception) {
            // 静默失败，不影响游戏
        }
    }

    /**
     * 添加一条记录，返回插入后的排名（1-based，0 表示未上榜）。
     *
     * ⚠️ 同分同名的记录必须各自占据独立名次：
     *    所以这里直接记录插入前的元素个数来定位，而不是事后按内容反查。
     */
    fun addEntry(name: String, survivalTime: Double): Int {
        val entry = Entry(
            name = name.trim().ifEmpty { "匿名" },
            time = (Math.round(survivalTime * 100) / 100.0).toFloat(),
            date = SimpleDateFormat("yyyy-MM-dd HH:mm", Locale.getDefault()).format(Date())
        )

        // 找到插入位置：按 time 倒序，同分时后加入的排在后面
        var insertAt = entries.size
        for (i in entries.indices) {
            if (entries[i].time < entry.time) {
                insertAt = i
                break
            }
        }
        entries.add(insertAt, entry)

        // 保留前 5
        while (entries.size > MAX_ENTRIES) {
            entries.removeAt(entries.size - 1)
        }
        save()

        return insertAt + 1
    }

    /**
     * 判断某个分数是否值得上榜。
     *
     * 0 秒（即时死亡）不视为上榜分数，避免空榜时玩家还没开始就被提示输入名字。
     */
    fun isHighScore(survivalTime: Double): Boolean {
        if (survivalTime <= 0.0) return false
        if (entries.size < MAX_ENTRIES) return true
        return survivalTime > entries[entries.size - 1].time
    }

    fun clear() {
        entries.clear()
        save()
    }

    val size: Int get() = entries.size

    operator fun get(index: Int): Entry = entries[index]

    companion object {
        const val MAX_ENTRIES = 5
        private const val PREFS_NAME = "isman100_leaderboard"
        private const val KEY_ENTRIES = "entries"
    }
}
