"""Bundled AI-generated interface translations; no translation network requests."""
LANGUAGES = {'en': 'English', 'de': 'Deutsch', 'es': 'Español', 'fr': 'Français', 'ja': '日本語', 'zh': '简体中文'}
# Rows: stable key | English | German | Spanish | French | Japanese | Simplified Chinese.
_ROWS = '''
midi|MIDI files|MIDI-Dateien|Archivos MIDI|Fichiers MIDI|MIDIファイル|MIDI 文件
text|Text sheet|Text-Sheet|Partitura de texto|Partition texte|テキスト楽譜|文本乐谱
collection|My songs|Meine Songs|Mis canciones|Mes morceaux|マイソング|我的歌曲
settings|Settings|Einstellungen|Ajustes|Paramètres|設定|设置
fine|FINE TUNING|FEINABSTIMMUNG|AJUSTES FINOS|RÉGLAGES FINS|詳細調整|精细调整
title|Sheet title|Sheet-Titel|Título de la partitura|Titre de la partition|楽譜のタイトル|乐谱名称
tone|Guitar tone|Gitarrenklang|Sonido de guitarra|Son de guitare|ギター音色|吉他音色
clean|Clean|Clean|Limpio|Clair|クリーン|清音
distortion|Distortion|Distortion|Distorsión|Distorsion|ディストーション|失真
transpose|Transpose|Transponieren|Transponer|Transposer|移調|移调
voices|Simultaneous notes|Gleichzeitige Noten|Notas simultáneas|Notes simultanées|同時発音数|同时发声数
range|Pitch range|Tonumfang|Rango de notas|Tessiture|音域|音域
fold|Octave fold|Oktaven anpassen|Ajustar octavas|Replier par octaves|オクターブ調整|八度折叠
drop|Drop outside range|Noten außerhalb entfernen|Omitir notas fuera del rango|Ignorer les notes hors tessiture|音域外の音を除外|忽略音域外音符
reject|Reject outside range|Bei Überschreitung abbrechen|Rechazar notas fuera del rango|Refuser les notes hors tessiture|音域外で変換を中止|遇到音域外音符时停止
trim|Trim silence before the first note|Stille vor der ersten Note kürzen|Recortar silencio inicial|Couper le silence initial|最初の音までの無音を除去|移除首音前的静音
create|Create & install sheet|Sheet erstellen & installieren|Crear e instalar partitura|Créer et installer la partition|楽譜を作成してインストール|创建并安装乐谱
code|LOCAL SHEET CODE|LOKALER SHEET-CODE|CÓDIGO LOCAL|CODE LOCAL|ローカル楽譜コード|本地乐谱代码
copy|Copy code|Code kopieren|Copiar código|Copier le code|コードをコピー|复制代码
library|MIDI LIBRARY|MIDI-BIBLIOTHEK|BIBLIOTECA MIDI|BIBLIOTHÈQUE MIDI|MIDIライブラリ|MIDI 曲库
browse|Open MIDI…|MIDI öffnen…|Abrir MIDI…|Ouvrir un MIDI…|MIDIを開く…|打开 MIDI…
refresh|Refresh|Aktualisieren|Actualizar|Actualiser|更新|刷新
library_hint|Choose a MIDI library folder in Settings, or open an individual MIDI file.|Wähle in den Einstellungen eine MIDI-Bibliothek oder öffne eine einzelne MIDI-Datei.|Elige una carpeta MIDI en Ajustes o abre un archivo MIDI.|Choisissez un dossier MIDI dans les paramètres ou ouvrez un fichier MIDI.|設定でMIDIフォルダーを指定するか、MIDIファイルを開いてください。|在设置中选择 MIDI 曲库文件夹，或打开单个 MIDI 文件。
library_empty|No MIDI files found in this folder.|Keine MIDI-Dateien in diesem Ordner gefunden.|No se encontraron archivos MIDI en esta carpeta.|Aucun fichier MIDI trouvé dans ce dossier.|このフォルダーにMIDIファイルはありません。|此文件夹中没有 MIDI 文件。
no_midi|No MIDI file selected|Keine MIDI-Datei ausgewählt|Ningún MIDI seleccionado|Aucun MIDI sélectionné|MIDIファイル未選択|尚未选择 MIDI 文件
tracks|CHOOSE YOUR TRACKS|SPUREN AUSWÄHLEN|SELECCIONA LAS PISTAS|CHOISISSEZ VOS PISTES|トラックを選択|选择音轨
all|Select all|Alle auswählen|Seleccionar todo|Tout sélectionner|すべて選択|全选
clear|Clear|Auswahl aufheben|Desmarcar todo|Tout désélectionner|選択解除|取消全选
use|USE|NUTZEN|USAR|UTILISER|使用|使用
track|TRACK|SPUR|PISTA|PISTE|トラック|音轨
channel|CH.|KAN.|CAN.|CAN.|CH.|通道
notes|NOTES|NOTEN|NOTAS|NOTES|音符数|音符数
pitch|RANGE|UMFANG|RANGO|TESSITURE|音域|音域
role|ROLE|ROLLE|FUNCIÓN|RÔLE|役割|角色
lead|Lead|Lead|Principal|Mélodie|リード|主旋律
normal|Normal|Normal|Normal|Normal|通常|普通
background|Background|Begleitung|Acompañamiento|Accompagnement|伴奏|伴奏
percussion|percussion|Schlagzeug|percusión|percussions|打楽器|打击乐
tracks_hint|Percussion is excluded. Lead parts take priority during conversion.|Schlagzeug ist ausgeschlossen. Lead-Spuren werden bei der Konvertierung bevorzugt.|La percusión se excluye. Las pistas principales tienen prioridad al convertir.|Les percussions sont exclues. Les pistes mélodiques sont prioritaires lors de la conversion.|打楽器は除外されます。変換時はリードを優先します。|不包含打击乐。转换时优先保留主旋律音轨。
sustain|Read MIDI sustain pedal|MIDI-Sustain-Pedal auswerten|Leer pedal de sustain MIDI|Lire la pédale de sustain MIDI|MIDIサステインペダルを読み取る|读取 MIDI 延音踏板
speed|Speed|Geschwindigkeit|Velocidad|Vitesse|速度|速度
play|Play|Abspielen|Reproducir|Lire|再生|播放
pause|Pause|Pause|Pausar|Pause|一時停止|暂停
stop|Stop|Stopp|Detener|Arrêter|停止|停止
volume|Preview volume|Vorschau-Lautstärke|Volumen de vista previa|Volume d’écoute|プレビュー音量|试听音量
preview_hint|Only tracks checked under USE are audible. Preview uses a neutral built-in synth.|Nur unter NUTZEN aktivierte Spuren sind hörbar. Die Vorschau nutzt einen neutralen Synthesizer.|Solo se oyen las pistas marcadas en USAR. La vista previa usa un sintetizador neutro.|Seules les pistes cochées sont audibles. L’écoute utilise un synthétiseur neutre.|選択したトラックのみ再生します。音色は内蔵シンセです。|仅播放勾选的音轨。试听使用内置中性合成音色。
layout|KEYBOARD LAYOUT|NOTATIONSBELEGUNG|DISTRIBUCIÓN DE NOTAS|DISPOSITION DES NOTES|音符の配列|音符布局
mapping|View / edit mapping|Belegung ansehen / bearbeiten|Ver / editar asignación|Voir / modifier les touches|割り当てを表示・編集|查看／编辑映射
syntax|Syntax guide|Syntax-Hilfe|Guía de sintaxis|Guide de syntaxe|記法ガイド|语法说明
paste|Paste keyboard letters, chords and rests below.|Füge unten Notenbuchstaben, Akkorde und Pausen ein.|Pega las letras, acordes y silencios abajo.|Collez les lettres, accords et silences ci-dessous.|音符の文字、和音、休符を入力してください。|在下方粘贴音符字母、和弦与休止符。
bpm|Tempo (BPM)|Tempo (BPM)|Tempo (BPM)|Tempo (BPM)|テンポ (BPM)|速度 (BPM)
steps|Steps per beat|Schritte pro Schlag|Pasos por pulso|Pas par temps|1拍あたりのステップ|每拍步数
gate|Note length|Notenlänge|Duración de las notas|Durée des notes|音符の長さ|音符时值
fit|Set target length and calculate tempo automatically|Länge vorgeben und Tempo automatisch berechnen|Fijar duración y calcular tempo automáticamente|Définir la durée et calculer le tempo automatiquement|長さを指定してテンポを自動計算|设置目标时长并自动计算速度
target|Target length|Gewünschte Länge|Duración deseada|Durée souhaitée|目標の長さ|目标时长
example|Insert example|Beispiel einfügen|Insertar ejemplo|Insérer un exemple|例を挿入|插入示例
text_hint|Each note/chord takes one step. Spaces separate tokens; dashes add rests.|Jede Note / jeder Akkord dauert einen Schritt. Leerzeichen trennen, Bindestriche setzen Pausen.|Cada nota/acorde ocupa un paso. Los espacios separan; los guiones añaden silencios.|Chaque note/accord dure un pas. Les espaces séparent ; les tirets ajoutent des silences.|音符・和音は1ステップです。空白は区切り、ハイフンは休符です。|每个音符／和弦占一步。空格用于分隔，连字符表示休止。
custom|Custom key mapping|Eigene Notenbelegung|Asignación personalizada|Touches personnalisées|カスタム割り当て|自定义映射
quarter|1 · quarter notes|1 · Viertelnoten|1 · negras|1 · noires|1 · 4分音符|1 · 四分音符
eighth|2 · eighth notes|2 · Achtelnoten|2 · corcheas|2 · croches|2 · 8分音符|2 · 八分音符
sixteenth|4 · sixteenth notes|4 · Sechzehntelnoten|4 · semicorcheas|4 · doubles croches|4 · 16分音符|4 · 十六分音符
thirtysecond|8 · thirty-second notes|8 · Zweiunddreißigstelnoten|8 · fusas|8 · triples croches|8 · 32分音符|8 · 三十二分音符
destination|INSTALL DESTINATION|INSTALLATIONSORDNER|CARPETA DE INSTALACIÓN|DOSSIER D’INSTALLATION|インストール先|安装目录
folder|Choose folder…|Ordner wählen…|Elegir carpeta…|Choisir un dossier…|フォルダーを選択…|选择文件夹…
destination_hint|Choose the GuitarNotes folder used by your active NTE installation.|Wähle den GuitarNotes-Ordner deiner aktiven NTE-Installation.|Elige la carpeta GuitarNotes de tu instalación activa de NTE.|Choisissez le dossier GuitarNotes de votre installation NTE active.|使用中のNTEのGuitarNotesフォルダーを選んでください。|选择当前 NTE 安装使用的 GuitarNotes 文件夹。
language|Language|Sprache|Idioma|Langue|言語|语言
ai_notice|Translations are AI-generated and may contain errors.|Die Übersetzungen wurden mit KI erstellt und können Fehler enthalten.|Las traducciones se han generado con IA y pueden contener errores.|Les traductions sont générées par IA et peuvent contenir des erreurs.|翻訳はAI生成のため、誤りが含まれる場合があります。|翻译由人工智能生成，可能包含错误。
appearance|Appearance|Darstellung|Apariencia|Apparence|外観|外观
light|Light mode|Heller Modus|Modo claro|Mode clair|ライトモード|浅色模式
dark|Dark mode|Dunkler Modus|Modo oscuro|Mode sombre|ダークモード|深色模式
save|Save|Speichern|Guardar|Enregistrer|保存|保存
cancel|Cancel|Abbrechen|Cancelar|Annuler|キャンセル|取消
settings_hint|Changes apply immediately when you save.|Änderungen werden beim Speichern angewendet.|Los cambios se aplican al guardar.|Les changements s’appliquent à l’enregistrement.|保存すると変更が反映されます。|保存后立即应用更改。
search|Search songs…|Songs suchen…|Buscar canciones…|Rechercher des morceaux…|曲を検索…|搜索歌曲…
song|SONG|SONG|CANCIÓN|MORCEAU|曲名|歌曲
length|LENGTH|LÄNGE|DURACIÓN|DURÉE|長さ|时长
open_folder|Open GuitarNotes|GuitarNotes öffnen|Abrir GuitarNotes|Ouvrir GuitarNotes|GuitarNotesを開く|打开 GuitarNotes
unnamed|Unnamed sheet · {code}|Unbenanntes Sheet · {code}|Partitura sin título · {code}|Partition sans titre · {code}|無題の楽譜 · {code}|未命名乐谱 · {code}
collection_hint|Sheets in your GuitarNotes folder. Names are recovered from this app’s current and previous export reports.|Sheets im GuitarNotes-Ordner. Namen werden aus aktuellen und früheren Exportberichten dieser App übernommen.|Partituras de GuitarNotes. Los nombres se recuperan de los informes de exportación actuales y anteriores.|Partitions du dossier GuitarNotes. Les noms sont retrouvés dans les anciens et nouveaux rapports d’exportation.|GuitarNotes内の楽譜です。現在・旧版のエクスポート記録から曲名を復元します。|显示 GuitarNotes 文件夹中的乐谱，并从新旧版本的导出记录中恢复名称。
no_sheets|No sheets found. Choose GuitarNotes in Settings or create your first sheet.|Keine Sheets gefunden. Wähle GuitarNotes in den Einstellungen oder erstelle ein Sheet.|No hay partituras. Elige GuitarNotes en Ajustes o crea una partitura.|Aucune partition. Choisissez GuitarNotes dans les paramètres ou créez une partition.|楽譜がありません。設定でGuitarNotesを選ぶか、楽譜を作成してください。|未找到乐谱。请在设置中选择 GuitarNotes，或创建第一份乐谱。
sharing_title|LOCAL CODES & SHARING|LOKALE CODES & TEILEN|CÓDIGOS LOCALES Y COMPARTIR|CODES LOCAUX ET PARTAGE|ローカルコードと共有|本地代码与分享
sharing|Codes created here work only locally. Other players cannot use them. To share a Music Sheet: enter its local code in NTE, play it on the guitar, and record the entire performance from beginning to end. Stop the recording, then publish your work at Bagel. Other players can use the new share code created by the game after publication.|Die hier erstellten Codes sind nur lokal nutzbar. Andere Spieler können sie nicht verwenden. Zum Teilen eines Music Sheets: Gib den lokalen Code in NTE ein, spiele das Sheet auf der Gitarre ab und nimm es von Anfang bis Ende auf. Stoppe die Aufnahme und veröffentliche dein Werk bei Bagel. Erst danach können andere Spieler den neuen, vom Spiel erstellten Freigabecode nutzen.|Los códigos creados aquí solo funcionan localmente. Otros jugadores no pueden usarlos. Para compartir: introduce el código local en NTE, reproduce la partitura con la guitarra y graba toda la interpretación de principio a fin. Detén la grabación y publica tu obra en Bagel. Los demás podrán usar el nuevo código que genere el juego tras publicarla.|Les codes créés ici sont uniquement locaux. Les autres joueurs ne peuvent pas les utiliser. Pour partager : saisissez le code local dans NTE, jouez la partition à la guitare et enregistrez-la du début à la fin. Arrêtez l’enregistrement, puis publiez votre œuvre chez Bagel. Les autres joueurs pourront utiliser le nouveau code créé par le jeu après publication.|ここで作成するコードはローカル専用で、他のプレイヤーは使用できません。共有するには、NTEでローカルコードを入力し、ギターで楽譜を再生して最初から最後まで録音してください。録音を停止し、Bagelで公開すると、ゲームが作成した新しい共有コードを他のプレイヤーが使用できます。|此处生成的代码仅能在本地使用，其他玩家无法使用。若要分享乐谱，请在 NTE 中输入本地代码，用吉他播放，并从头到尾录制。停止录制后，在 Bagel 发布作品。发布后，其他玩家才能使用游戏新生成的分享代码。
ready|Ready.|Bereit.|Listo.|Prêt.|準備完了。|就绪。
reading|Reading MIDI and analyzing tracks…|MIDI lesen und Spuren analysieren…|Leyendo MIDI y analizando pistas…|Lecture du MIDI et analyse des pistes…|MIDIを読み込み、解析中…|正在读取 MIDI 并分析音轨…
loaded|MIDI loaded. Choose tracks, then create your sheet.|MIDI geladen. Wähle Spuren und erstelle dein Sheet.|MIDI cargado. Elige las pistas y crea la partitura.|MIDI chargé. Choisissez les pistes, puis créez la partition.|MIDIを読み込みました。トラックを選んで楽譜を作成してください。|MIDI 已加载。选择音轨后即可创建乐谱。
converting|Converting and installing sheet…|Sheet konvertieren und installieren…|Convirtiendo e instalando…|Conversion et installation…|変換・インストール中…|正在转换并安装乐谱…
installed|Installed: {title}|Installiert: {title}|Instalado: {title}|Installé : {title}|インストール済み: {title}|已安装：{title}
copied|Local sheet code copied.|Lokalen Sheet-Code kopiert.|Código local copiado.|Code local copié.|ローカルコードをコピーしました。|已复制本地代码。
error|Could not finish|Vorgang fehlgeschlagen|No se pudo completar|Impossible de terminer|処理に失敗しました|无法完成
input_error|Check your input and settings.|Prüfe deine Eingaben und Einstellungen.|Revisa los datos y los ajustes.|Vérifiez la saisie et les paramètres.|入力と設定を確認してください。|请检查输入和设置。
error_details|Technical details|Technische Details|Detalles técnicos|Détails techniques|技術的な詳細|技术详情
need_midi|Choose a MIDI file first.|Wähle zuerst eine MIDI-Datei.|Elige primero un archivo MIDI.|Choisissez d’abord un fichier MIDI.|先にMIDIファイルを選んでください。|请先选择 MIDI 文件。
need_tracks|Select at least one non-percussion track.|Wähle mindestens eine Spur ohne Schlagzeug.|Selecciona al menos una pista sin percusión.|Sélectionnez au moins une piste non percussive.|打楽器以外のトラックを1つ以上選択してください。|请至少选择一条非打击乐音轨。
need_folder|Choose an absolute GuitarNotes folder path in Settings.|Wähle in den Einstellungen einen absoluten GuitarNotes-Pfad.|Elige una ruta absoluta a GuitarNotes en Ajustes.|Choisissez un chemin absolu vers GuitarNotes dans les paramètres.|設定でGuitarNotesの絶対パスを指定してください。|请在设置中选择 GuitarNotes 的绝对路径。
choose_midi|Choose a MIDI file|MIDI-Datei wählen|Elegir archivo MIDI|Choisir un fichier MIDI|MIDIファイルを選択|选择 MIDI 文件
wait|Please wait for the current operation to finish.|Bitte warte, bis der aktuelle Vorgang beendet ist.|Espera a que termine la operación actual.|Veuillez attendre la fin de l’opération.|現在の処理が完了するまでお待ちください。|请等待当前操作完成。
reading_collection|Reading your sheet collection…|Sammlung einlesen…|Leyendo la colección…|Lecture de la collection…|楽譜を読み込み中…|正在读取乐谱收藏…
collection_count|{count} sheets · {warnings} unreadable files|{count} Sheets · {warnings} nicht lesbare Dateien|{count} partituras · {warnings} archivos ilegibles|{count} partitions · {warnings} fichiers illisibles|{count}件の楽譜・{warnings}件の読み取りエラー|{count} 份乐谱 · {warnings} 个文件无法读取
file_info|{name} · {time} · {parts} parts|{name} · {time} · {parts} Spuren|{name} · {time} · {parts} pistas|{name} · {time} · {parts} pistes|{name} · {time} · {parts}トラック|{name} · {time} · {parts} 条音轨
auto_tempo|Automatic tempo: {bpm} BPM · Steps per beat: {steps} (unchanged).|Automatisches Tempo: {bpm} BPM · Schritte pro Schlag: {steps} (unverändert).|Tempo automático: {bpm} BPM · Pasos por pulso: {steps} (sin cambios).|Tempo automatique : {bpm} BPM · Pas par temps : {steps} (inchangés).|自動テンポ: {bpm} BPM・1拍: {steps}ステップ（変更なし）。|自动速度：{bpm} BPM · 每拍 {steps} 步（不变）。
text_duration|Text length: {seconds} s. Export applies silence trimming, lead-in and tail afterward.|Textlänge: {seconds} s. Stille-Kürzung, Vor- und Nachlauf werden danach angewendet.|Duración: {seconds} s. El recorte y los márgenes se aplican después.|Durée : {seconds} s. Le silence et les marges sont ajustés ensuite.|テキストの長さ: {seconds}秒。無音除去と前後の余白は書き出し時に適用します。|文本时长：{seconds} 秒。静音裁剪及前后留白会在导出时另行应用。
fit_hint|Target length includes written rests, before trimming and the 0.8 s lead-in / 1.5 s tail.|Die Länge enthält notierte Pausen, vor Kürzung sowie 0,8 s Vorlauf / 1,5 s Nachlauf.|La duración incluye silencios escritos, antes del recorte y los márgenes de 0,8 s / 1,5 s.|La durée inclut les silences écrits, avant les marges de 0,8 s / 1,5 s et le rognage.|目標の長さには休符を含みます。無音除去と前0.8秒・後1.5秒の余白は別です。|目标时长包含休止符，但不包含裁剪处理以及 0.8 秒前置／1.5 秒后置留白。
syntax_text|a b c: consecutive notes. [abc] or {abc}: chord. (abc): fast roll. - or vertical bar: one rest; _: two rests. Spaces and line breaks add no time. // starts a comment. Escape reserved keys with a backslash. Uppercase/shifted Virtual Piano letters represent black keys.|a b c: aufeinanderfolgende Noten. [abc] oder {abc}: Akkord. (abc): schneller Lauf. - oder senkrechter Strich: eine Pause; _: zwei Pausen. Leerzeichen und Zeilenumbrüche verlängern nichts. // beginnt einen Kommentar. Reservierte Zeichen mit Backslash maskieren. Großbuchstaben / Umschaltzeichen in Virtual Piano stehen für schwarze Tasten.|a b c: notas seguidas. [abc] o {abc}: acorde. (abc): secuencia rápida. - o barra vertical: un silencio; _: dos. Los espacios y saltos no añaden tiempo. // inicia un comentario. Escapa teclas reservadas con barra inversa. Mayúsculas y símbolos de Virtual Piano son teclas negras.|a b c : notes successives. [abc] ou {abc} : accord. (abc) : arpège rapide. - ou barre verticale : un silence ; _ : deux. Espaces et retours n’ajoutent aucun temps. // commence un commentaire. Échappez les touches réservées avec une barre oblique inverse. Majuscules et symboles Virtual Piano : touches noires.|a b c: 順番に演奏。[abc]・{abc}: 和音。(abc): 速い連続音。-・縦線: 休符1個、_: 2個。空白・改行は時間を追加しません。// はコメント。予約記号はバックスラッシュでエスケープします。Virtual Pianoの大文字・シフト記号は黒鍵です。|a b c：依次演奏。[abc] 或 {abc}：和弦。(abc)：快速琶音。- 或竖线：一步休止；_：两步。空格和换行不增加时间。// 开始注释。保留字符需用反斜杠转义。Virtual Piano 的大写字母与 Shift 符号代表黑键。
replace|Replace the current text with the example?|Aktuellen Text durch das Beispiel ersetzen?|¿Reemplazar el texto actual por el ejemplo?|Remplacer le texte actuel par l’exemple ?|現在のテキストを例で置き換えますか？|是否用示例替换当前文本？
'''
CATALOGS = {code: {} for code in LANGUAGES}
for row in _ROWS.strip().splitlines():
    key, *values = row.split('|')
    if len(values) != 6:
        raise RuntimeError(f'Invalid translation row: {key}')
    for code, value in zip(LANGUAGES, values):
        CATALOGS[code][key] = value

def translate(language, key, **values):
    return CATALOGS.get(language, CATALOGS['en']).get(key, CATALOGS['en'].get(key, key)).format(**values) if values else CATALOGS.get(language, CATALOGS['en']).get(key, CATALOGS['en'].get(key, key))

_ALIASES = {'custom_mapping': 'custom', 'fine_tuning': 'fine', 'replace_text': 'replace', 'select_tracks': 'need_tracks', 'sheet_title': 'title', 'tempo': 'bpm'}
for catalog in CATALOGS.values():
    for alias, original in _ALIASES.items(): catalog[alias] = catalog[original]
for language, value in zip(LANGUAGES, ('Untitled sheet', 'Unbenanntes Sheet', 'Partitura sin título', 'Partition sans titre', '無題の楽譜', '未命名乐谱')):
    CATALOGS[language]['untitled'] = value
for language, value in zip(LANGUAGES, ('Check the notation and target length (20–400 BPM).', 'Prüfe die Notation und gewünschte Länge (20–400 BPM).', 'Revisa la notación y duración (20–400 BPM).', 'Vérifiez la notation et la durée (20–400 BPM).', '記法と目標の長さを確認してください（20～400 BPM）。', '请检查记谱和目标时长（20–400 BPM）。')):
    CATALOGS[language]['timing_error'] = value
