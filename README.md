# TaskFlow-app

TaskFlow-app は、Flask と Docker で構築されたシンプルなToDoアプリケーションです。ユーザー認証、タスクのCRUD操作、データベースマイグレーションなどの基本的な機能を備えています。

## ✨ 主な機能
ユーザー認証:
  - 安全なサインアップ、ログイン、ログアウト機能
  - ユーザープロフィールの編集（パスワード変更）
タスク管理 (CRUD): タスクの追加、一覧表示、編集、削除

タスク状態管理: タスクの完了・未完了の切り替え

データベースマイグレーション: Flask-Migrateによるスキーマ変更管理
## 🛠️ 技術スタック
バックエンド: Flask

フロントエンド: HTML, Tailwind CSS

データベース: PostgreSQL

コンテナ化: Docker, Docker Compose

CI: GitHub Actions

Pythonライブラリ: Flask-SQLAlchemy, Flask-Login, Flask-Migrateなど（詳細はrequirements.txtを参照）

## 🚀 はじめに (Getting Started)

### 前提条件

- Docker Engine
- Docker Compose (Docker Desktop for Mac/Windows には含まれています)

1. リポジトリをクローン
```bash
git clone https://github.com/cosbytoru/TaskFlow-app.git
cd taskflow-app
```

2. コンテナのビルドと起動

以下のコマンドで、Dockerコンテナをビルドし、バックグラウンドで起動します。
```bash
docker compose up --build -d
```
初回起動時にはイメージのビルドに数分かかることがあります。

3. データベースのマイグレーション

以下のコマンドを実行してデータベースのマイグレーション（テーブル作成や更新）を行います。初回起動時やモデル変更後に実行してください。
```bash
docker compose exec web flask db upgrade
```

4. アプリケーションへのアクセス

ブラウザで `http://localhost:5001` にアクセスしてください。

## 🔧 開発者向け情報 (For Developers)

### データベースのスキーマ更新

`app.py` 内のモデル（`User`クラスや`Task`クラス）に変更を加えた場合は、以下の手順でデータベースのスキーマを更新します。

1. **マイグレーションファイルの自動生成:** モデルの変更点を検出し、更新用のマイグレーションファイルを生成します。
   ```bash
   docker compose exec web flask db migrate -m "変更内容の要約（例: Add due_date to Task）"
   ```
2. **データベースへの適用:** 生成されたファイルを元に、データベースのテーブル構造を更新します。
   ```bash
   docker compose exec web flask db upgrade
   ```

   
### 静的解析 (Linting)

`flake8` を使用してコードの静的解析を実行できます。
```bash
docker compose run --rm web flake8 .
```

### テスト実行 (Testing)
`pytest` を使用してテストを実行できます。
```bash
docker compose run --rm web pytest
```










'================================================================================
' ■■■ メイン処理② (XLSXファイル結合) ★★★ 個別設定対応版 ★★★
'================================================================================
Public Sub CombineXlsxFilesByMaster()

    ' ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
    ' ★                                                            ★
    ' ★               Excelファイル用の設定                        ★
    ' ★                                                            ★
    ' ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★

    ' 1. 読み込むExcelファイルのヘッダーとデータの【デフォルト】開始位置
    Const HEADER_ROW As Long = 4     ' ヘッダーのある行 (4行目)
    Const DEFAULT_DATA_START_ROW As Long = 5 ' デフォルトのデータ開始行
    Const DATA_START_COL As Long = 2 ' データ開始列 (B列から)

    ' --- 初期設定 ---
    Dim fso As Object, fileGroups As Object, targetFolder As Object, file As Object
    Dim folderPath As String, sheetName As String, filePath As String, sourceName As String
    Dim masterName As Variant
    Dim ws As Worksheet, sourceWb As Workbook, sourceWs As Worksheet
    Dim lineCounter As Long, i As Long

    ' --- ユーザーにフォルダを選択させる ---
    With Application.FileDialog(4) ' msoFileDialogFolderPicker
        .Title = "XLSXファイルが保存されているフォルダを選択してください"
        If .Show = False Then Exit Sub
        folderPath = .SelectedItems(1)
    End With
    
    ' --- オブジェクトを準備 ---
    On Error GoTo ErrorHandler_Xlsx
    Set fso = CreateObject("Scripting.FileSystemObject")
    Set fileGroups = CreateObject("Scripting.Dictionary")
    Set targetFolder = fso.GetFolder(folderPath)
    
    ' --- ステップ1: XLSXファイルをマスタ名でグループ化 ---
    For Each file In targetFolder.Files
        If LCase(file.name) Like "移行用シート_*.xlsx" Then
            Dim baseName As String
            baseName = fso.GetBaseName(file.name)

            Dim firstUnderscorePos As Long, secondUnderscorePos As Long
            firstUnderscorePos = InStr(1, baseName, "_")
            If firstUnderscorePos > 0 Then
                secondUnderscorePos = InStr(firstUnderscorePos + 1, baseName, "_")
                If secondUnderscorePos > 0 Then
                    sourceName = Mid(baseName, secondUnderscorePos + 1)
                    masterName = Mid(baseName, firstUnderscorePos + 1, secondUnderscorePos - firstUnderscorePos - 1)

                    If Not fileGroups.Exists(masterName) Then
                        fileGroups.Add masterName, New Collection
                    End If
                    fileGroups(masterName).Add Array(file.Path, sourceName)
                End If
            End If
        End If
    Next file

    If fileGroups.Count = 0 Then
        MsgBox "対象となるXLSXファイルが見つかりませんでした。", vbInformation
        GoTo CleanUp_Xlsx
    End If
    
    Application.ScreenUpdating = False
    Application.DisplayAlerts = False ' Excelの警告を非表示
    
    ' --- ステップ2: グループごとにシートを作成し、データを結合 ---
    For Each masterName In fileGroups.Keys
        sheetName = SanitizeSheetName(CStr(masterName) & "_xlsx")
        
        '--- 変数の準備 ---
        Dim dataStartRow As Long
        Dim fixedColumnCount As Long
        
        '----------------------------------------------------------------------
        ' ★★★ マスタごとの個別設定エリア ★★★
        '----------------------------------------------------------------------
        ' ここでマスタごとの「データ開始行」と「取得する列数」を指定します。
        ' fixedColumnCount を 0 にすると、列数は自動で検出されます。
        
        Select Case masterName
            Case "事業体マスタ"
                dataStartRow = 10
                fixedColumnCount = 0 ' 例: Y列までなら 24 を指定 (B列から数えて24列)
                
            ' --- 他のマスタもここに追加できます ---
            'Case "スキームマスタ"
            '    dataStartRow = 5
            '    fixedColumnCount = 24 ' Y列まで取得
            
            Case Else
                ' 上記で指定されなかったマスタは、デフォルト設定を使います
                dataStartRow = DEFAULT_DATA_START_ROW
                fixedColumnCount = 0 ' 列数は自動検出
        End Select
        '----------------------------------------------------------------------
    
        On Error Resume Next
        Set ws = Nothing
        Set ws = ThisWorkbook.Worksheets(sheetName)
        On Error GoTo ErrorHandler_Xlsx
    
        If ws Is Nothing Then
            Set ws = ThisWorkbook.Worksheets.Add(After:=ThisWorkbook.Worksheets(ThisWorkbook.Worksheets.Count))
            ws.name = sheetName
            ws.Cells.NumberFormat = "@"
        Else
            ws.Cells.ClearContents
            ws.Cells.NumberFormat = "@"
        End If

        lineCounter = 2 ' データは2行目から書き始める

        Dim fileList As Collection
        Set fileList = fileGroups(masterName)
        
        ' ヘッダーを最初のファイルから動的に取得
        If fileList.Count > 0 Then
            Dim firstFileInfo As Variant
            firstFileInfo = fileList.Item(1)
            Set sourceWb = Workbooks.Open(firstFileInfo(0), ReadOnly:=True)
            Set sourceWs = sourceWb.Worksheets(1)
            
            Dim lastHeaderCol As Long
            lastHeaderCol = sourceWs.Cells(HEADER_ROW, sourceWs.Columns.Count).End(xlToLeft).Column
            
            If lastHeaderCol >= DATA_START_COL Then
                Dim headers As Variant
                headers = sourceWs.Range(sourceWs.Cells(HEADER_ROW, DATA_START_COL), sourceWs.Cells(HEADER_ROW, lastHeaderCol)).Value
                
                Dim finalHeaders() As Variant
                ReDim finalHeaders(1 To 1, 1 To UBound(headers, 2) + 1)
                finalHeaders(1, 1) = "ファイル名"
                
                Dim c As Long
                For c = 1 To UBound(headers, 2)
                    finalHeaders(1, c + 1) = headers(1, c)
                Next c
                
                ws.Cells(1, 1).Resize(1, UBound(finalHeaders, 2)).Value = finalHeaders
            Else
                ws.Cells(1, 1).Value = "ファイル名"
            End If
            
            sourceWb.Close SaveChanges:=False
            Set sourceWb = Nothing
            Set sourceWs = Nothing
        End If

        For i = 1 To fileList.Count
            Dim fileInfo As Variant
            fileInfo = fileList.Item(i)
            filePath = fileInfo(0)
            sourceName = fileInfo(1)

            Set sourceWb = Workbooks.Open(filePath, ReadOnly:=True)
            Set sourceWs = sourceWb.Worksheets(1)
            
            Dim lastRow As Long, lastCol As Long
            lastRow = sourceWs.Cells(sourceWs.Rows.Count, DATA_START_COL).End(xlUp).Row

            If lastRow >= dataStartRow Then
                ' 固定列数の指定があるか確認
                If fixedColumnCount > 0 Then
                    ' 固定列数を採用
                    lastCol = DATA_START_COL + fixedColumnCount - 1
                Else
                    ' 動的に最終列を判定
                    Dim headerLastCol As Long, dataLastCol As Long
                    headerLastCol = sourceWs.Cells(HEADER_ROW, sourceWs.Columns.Count).End(xlToLeft).Column
                    dataLastCol = sourceWs.Cells(dataStartRow, sourceWs.Columns.Count).End(xlToLeft).Column
                    lastCol = Application.WorksheetFunction.Max(headerLastCol, dataLastCol)
                End If

                Dim dataRange As Range
                Set dataRange = sourceWs.Range(sourceWs.Cells(dataStartRow, DATA_START_COL), sourceWs.Cells(lastRow, lastCol))

                Dim dataArray As Variant
                dataArray = dataRange.Value

                If IsArray(dataArray) Then
                    Dim writeData() As Variant
                    Dim r As Long, c As Long
                    For r = 1 To UBound(dataArray, 1)
                        ReDim writeData(1 To UBound(dataArray, 2) + 1)
                        writeData(1) = sourceName
                        For c = 1 To UBound(dataArray, 2)
                            writeData(c + 1) = dataArray(r, c)
                        Next c
                        ws.Cells(lineCounter, 1).Resize(1, UBound(writeData)).Value = writeData
                        lineCounter = lineCounter + 1
                    Next r
                Else
                    If Not IsEmpty(dataArray) Then
                        ws.Cells(lineCounter, 1).Value = sourceName
                        ws.Cells(lineCounter, 2).Value = dataArray
                        lineCounter = lineCounter + 1
                    End If
                End If
            End If

            sourceWb.Close SaveChanges:=False
        Next i

        ws.Columns.AutoFit
    Next masterName
    
    MsgBox "XLSXファイルの結合処理が完了しました。", vbInformation

CleanUp_Xlsx:
    On Error Resume Next
    Application.ScreenUpdating = True
    Application.DisplayAlerts = True
    Set ws = Nothing
    Set sourceWs = Nothing
    If Not sourceWb Is Nothing Then sourceWb.Close False
    Set sourceWb = Nothing
    Set fileList = Nothing
    Set file = Nothing
    Set targetFolder = Nothing
    Set fileGroups = Nothing
    Set fso = Nothing
    Exit Sub
    
ErrorHandler_Xlsx:
    MsgBox "XLSXファイルの処理中にエラーが発生しました。" & vbCrLf & vbCrLf & _
           "エラー番号: " & Err.Number & vbCrLf & _
           "エラー内容: " & Err.Description, vbCritical
    GoTo CleanUp_Xlsx
End Sub
