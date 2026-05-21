BEGIN {
    for(i=29; i>=0; i--) {
        cmd = "date -v-" i "d +%Y-%m-%d"
        cmd | getline d
        close(cmd)
        date_array[29-i] = d
        punch_count[d] = 0
    }
}

/PUNCH SUBJECT=/ {
    match($1, /[0-9]{4}-[0-9]{2}-[0-9]{2}/)
    log_date = substr($1, RSTART, RLENGTH)
    for(f=1; f<=NF; f++) {
        if($f ~ /DURATION=/) {
            split($f, arr, "=")
            dur = arr[2] + 0
            punch_count[log_date] += dur
        }
    }
}

END {
    printf "   "
    for(i=0; i<30; i++) {
        d = date_array[i]
        mins = punch_count[d]
        if (mins == 0)
            printf "\033[48;5;235m  \033[0m "
        else if (mins > 0 && mins <= 30)
            printf "\033[48;5;22m  \033[0m "
        else if (mins > 30 && mins <= 60)
            printf "\033[48;5;40m  \033[0m "
        else
            printf "\033[48;5;46m  \033[0m "
            
        if ((i + 1) % 7 == 0) {
            printf "\n   "
        }
    }
    printf "\n"
}