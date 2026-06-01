BEGIN {
    # 构建 30 天日期索引矩阵，自动平滑适配 Linux (date -d) 和 macOS (date -v)
    for(i=29; i>=0; i--) {
        cmd = "date -d '" i " days ago' +%Y-%m-%d 2>/dev/null || date -v-" i "d +%Y-%m-%d"
        if ((cmd | getline d) > 0) {
            date_array[29-i] = d
            punch_count[d] = 0
        }
        close(cmd)
    }
}

# 解析标准结构化日志特征行
/PUNCH/ {
    # 动态抽取日志行头部包含的标准的 YYYY-MM-DD 格式
    if (match($0, /[0-9]{4}-[0-9]{2}-[0-9]{2}/)) {
        log_date = substr($0, RSTART, RLENGTH)
    }
    # 抽取 DURATION 各项键值
    for(f=1; f<=NF; f++) {
        if($f ~ /DURATION=/) {
            split($f, arr, "=")
            dur = arr[2] + 0
            punch_count[log_date] += dur
        }
    }
}

END {
    print "\n  ==== 终端心流打卡热力图看板 (AWK 解析引擎) ===="
    printf "   "
    for(i=0; i<30; i++) {
        d = date_array[i]
        mins = punch_count[d]

        if (mins == 0)
            printf "\033[48;5;235m  \033[0m "   # 空白：暗色
        else if (mins > 0 && mins <= 50)
            printf "\033[48;5;22m  \033[0m "    # 浅度专注：暗绿
        else if (mins > 50 && mins <= 100)
            printf "\033[48;5;40m  \033[0m "    # 中度专注：纯绿
        else
            printf "\033[48;5;46m  \033[0m "    # 高效心流：亮绿

        if ((i + 1) % 7 == 0) {
            printf "\n   "
        }
    }
    print "\n  ================================================="
}