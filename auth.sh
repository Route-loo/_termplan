
DB_PATH="/d/termplan/termplan.db"

COLOR_RESET="\033[0m"
COLOR_TITLE="\033[1;32m"  
COLOR_TEXT="\033[0;37m"   
COLOR_WARN="\033[1;31m"  
COLOR_SUCC="\033[1;36m"  


if ! command -v sqlite3 &> /dev/null; then
    echo -e "${COLOR_WARN}[错误] 核心集群缺失：检测到当前系统未安装 sqlite3 工具。${COLOR_RESET}"
    echo "请先运行: sudo apt install sqlite3 (Linux) 或检查环境变量"
    exit 1
fi


if [ ! -f "$DB_PATH" ]; then
    echo -e "${COLOR_WARN}[警告] 未检测到 $DB_PATH，将尝试原地初始化新数据节点...${COLOR_RESET}"
    sqlite3 "$DB_PATH" "CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT);"
fi


show_menu() {
    clear
    echo -e "${COLOR_TITLE}=======================================${COLOR_RESET}"
    echo -e "${COLOR_TITLE}     TermPlan — 专注与静谧的工作流     ${COLOR_RESET}"
    echo -e "${COLOR_TITLE}=======================================${COLOR_RESET}"
    echo -e " 系统状态 / ${COLOR_SUCC}终端鉴权节点${COLOR_RESET}"
    echo -e " 1. 验证登入 (Login)"
    echo -e " 2. 新成员接入 (Register)"
    echo -e " 3. 挂起断开 (Exit)"
    echo -e "${COLOR_TITLE}---------------------------------------${COLOR_RESET}"
    echo -ne "请输入调度指令 [1-3]: "
}

handle_login() {
    echo -e "\n${COLOR_SUCC}>>> 安全鉴权中心 · 登录验证${COLOR_RESET}"
    read -p "USERNAME: " username
    
    
    unset password
    prompt="PASSWORD: "
    while IFS= read -r -s -n1 -p "$prompt" char; do
        if [[ $char == $'\0' ]]; then
            break
        fi
        if [[ $char == $'\177' ]]; then
            if [ ${#password} -gt 0 ]; then
                password="${password%?}"
                echo -ne "\b \b"
            fi
        else
            password+="$char"
            echo -ne "*"
        fi
        prompt=""
    done
    echo

    if [ -z "$username" ] || [ -z "$password" ]; then
        echo -e "${COLOR_WARN}[错误] 鉴权字段溢出：用户名与密码不可为空白。${COLOR_RESET}"
        read -n 1 -s -p "按任意键返回主菜单..."
        return
    fi

    
    input_hash=$(echo -n "$password" | sha256sum | awk '{print $1}')

   
    db_pwd=$(sqlite3 "$DB_PATH" "SELECT password_hash FROM users WHERE username='$username';")

    
    if [ "$db_pwd" == "$input_hash" ]; then
        echo -e "\n${COLOR_TITLE}[成功] 安全鉴权通过！成功接入本地时序看板。${COLOR_RESET}"
        echo -e "欢迎回来，${COLOR_SUCC}$username${COLOR_RESET}。系统正为你同步热力矩阵...\n"
        read -n 1 -s -p "已成功登录，按任意键退出鉴权程序..."
        exit 0
    else
        echo -e "\n${COLOR_WARN}[失败] 鉴权未通过：用户名或密码不匹配，访问被拒绝。${COLOR_RESET}"
        read -n 1 -s -p "按任意键重新校验..."
    fi
}
handle_register() {
    echo -e "\n${COLOR_SUCC}>>> 新成员接入中心 · 账户部署${COLOR_RESET}"
    read -p "配置新成员用户名 (USERNAME): " username
    
    if [ -z "$username" ]; then
        echo -e "${COLOR_WARN}[错误] 用户名不可为空白。${COLOR_RESET}"
        read -n 1 -s -p "按任意键返回..."
        return
    fi

   
    exists=$(sqlite3 "$DB_PATH" "SELECT 1 FROM users WHERE username='$username';")
    if [ "$exists" == "1" ]; then
        echo -e "${COLOR_WARN}[冲突] 该用户节点在数据库中已存在，请勿重复部署。${COLOR_RESET}"
        read -n 1 -s -p "按任意键返回..."
        return
    fi

    read -s -p "配置登录密匙 (PASSWORD): " password
    echo
    
    if [ -z "$password" ]; then
        echo -e "${COLOR_WARN}[错误] 密码不可为空白。${COLOR_RESET}"
        read -n 1 -s -p "按任意键返回..."
        return
    fi

    
    register_hash=$(echo -n "$password" | sha256sum | awk '{print $1}')

    
    sqlite3 "$DB_PATH" "INSERT INTO users (username, password_hash) VALUES ('$username', '$register_hash');"
    
    if [ $? -eq 0 ]; then
        echo -e "${COLOR_TITLE}[成功] 节点部署完成！新成员 '$username' 已成功加密归档至数据库。${COLOR_RESET}"
        read -n 1 -s -p "按任意键切回登录界面..."
    else
        echo -e "${COLOR_WARN}[错误] 数据库写入异常，请检查权限。${COLOR_RESET}"
        read -n 1 -s -p "按任意键返回..."
    fi
}


while true; do
    show_menu
    read choice
    case $choice in
        1) handle_login ;;
        2) handle_register ;;
        3) echo -e "\n${COLOR_SUCC}已静谧退出。期待下一次专注流的开启。${COLOR_RESET}"; exit 0 ;;
        *) echo -e "${COLOR_WARN}\n[无效指令] 请输入 1、2 或 3${COLOR_RESET}"; sleep 1 ;;
    esac
done