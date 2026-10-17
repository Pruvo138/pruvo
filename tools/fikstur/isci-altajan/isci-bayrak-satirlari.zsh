# KAYNAK: ~/.claude/cron/isci.sh git hash-object a9b69f82bec6f0a3b1813d244b51f9683192e3b7 (18 Eki 2026), satir 1114,1115,1209,1410 BIREBIR (yama ONCESI)
ISCI_TALIMAT_PROMPTU="${PROMPT_BASI}Once $EV_KOKU/CLAUDE.md dosyasi varsa oku ve kurallarina uy. Sonra $SPEC_DOSYASI dosyasini oku ve icindeki gorevi harfiyen uygula. YALNIZCA o gorevi yap. Bu OTOMATIK bir kosumdur, kullanici YOK: soru sorma, kendi makul kararini ver."
CLAUDE_BAYRAKLAR=(--permission-mode bypassPermissions ${BUTCE_BAYRAK[@]+"${BUTCE_BAYRAK[@]}"} --output-format json)
  CLAUDE_BAYRAKLAR_2=(--permission-mode bypassPermissions ${BUTCE_BAYRAK[@]+"${BUTCE_BAYRAK[@]}"} --output-format json)
    KAPANIS_BAYRAKLAR=(--permission-mode bypassPermissions --max-budget-usd "$KAPANIS_BUTCE_USD" -r "$OTURUM_ID")
