# KAYNAK: ~/.claude/cron/isci.sh git hash-object 74481bcaa6bd73ef22a07e34ba16fff8ad0c5626 (20 Eki 2026), satir 1410-1413 BIREBIR (yama ONCESI); sarmalayan if/echo satirlari fikstur
if [[ -n "$KAPANIS_HALI" ]]; then
    KAPANIS_BAYRAKLAR=(--permission-mode bypassPermissions --disallowedTools Agent,Task,Workflow --max-budget-usd "$KAPANIS_BUTCE_USD" -r "$OTURUM_ID")
    ( trap - TERM INT EXIT; env "${CLAUDE_ENV[@]}" "$CLAUDE_BIN" -p "$KAPANIS_PROMPTU" "${KAPANIS_BAYRAKLAR[@]}" >> "$LOG" 2>&1 ) &
    wait $!   # ISCI-AYRIK: TERM/INT trap'i burada HEMEN calisir
    KAPANIS_RC=$?
    echo "KAPANIS_CAGRISI kapanis_rc=$KAPANIS_RC" >> "$LOG"
fi
