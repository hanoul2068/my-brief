Attribute VB_Name = "DefectTrend"
Option Explicit
' Defect Trend 로그용 그림 매크로 (개인용 매크로 통합 문서 PERSONAL.XLSB에 넣어 사용)
'   Ctrl+Shift+J : 복사한 그림을 JPEG로 붙여넣기
'                  - 트렌드 시트 : 선택한 칸 크기에 맞춤
'                  - 추가확인 시트 : 그 행의 마지막 그림 오른쪽에 행 높이로 이어 붙임
'   Ctrl+Shift+K : 그림 정리
'                  - 트렌드 시트 : 선택한 그림(여러 개 가능)을 각자 놓인 칸에 맞춤
'                  - 추가확인 시트 : 선택한 그림(또는 선택한 칸)이 있는 행의 그림을 왼쪽부터 다시 정렬
'   Ctrl+Shift+S : 'Trend' / 'Extra' 시트를 Case별로 정렬 (Case 발견순 -> 날짜순, 그림도 같이 이동)
'   Ctrl+Shift+U : (통합 파일에서) IC·CJ 파일을 그림까지 다시 불러와 통합 + 정렬
'   Ctrl+Shift+D : 'Trend' / 'Extra' 시트에서 기준일 이전 행의 그림만 삭제 (텍스트는 유지)

Private Const MARGIN As Double = 2   ' 칸 안쪽 여백 (pt)
Private Const GAP As Double = 6      ' 추가확인 시트 그림 사이 간격 (pt)

Public Sub PasteFit()
Attribute PasteFit.VB_ProcData.VB_Invoke_Func = "J\n14"
    Dim ws As Worksheet, tgt As Range, n As Long, bc As Long, r As Long, shp As Shape
    If TypeName(Selection) <> "Range" Then
        MsgBox "그림을 넣을 칸을 먼저 클릭하세요.", vbExclamation: Exit Sub
    End If
    If Not ClipHasPicture() Then
        MsgBox "복사된 그림이 없습니다. 캡처/그림을 복사한 뒤 다시 실행하세요.", vbExclamation: Exit Sub
    End If
    Set ws = ActiveSheet
    Set tgt = ActiveCell.MergeArea
    bc = BoardStartCol(ws)
    If bc > 0 Then
        ' 추가확인 시트: 행 끝에 이어 붙이기
        r = ActiveCell.Row
        If r < 2 Then MsgBox "2행부터 사용하세요.", vbExclamation: Exit Sub
        n = ws.Shapes.Count
        ws.Cells(r, bc).Select
        If Not TryPaste(ws, n) Then
            MsgBox "그림 붙여넣기에 실패했습니다.", vbExclamation: Exit Sub
        End If
        Set shp = ws.Shapes(ws.Shapes.Count)
        PlaceInRow shp, ws, r, RowRightEdge(ws, r, bc, shp.Name)
        tgt.Cells(1, 1).Select
        Exit Sub
    End If
    n = ws.Shapes.Count
    tgt.Cells(1, 1).Select
    If Not TryPaste(ws, n) Then
        MsgBox "그림 붙여넣기에 실패했습니다.", vbExclamation: Exit Sub
    End If
    FitToCell ws.Shapes(ws.Shapes.Count), tgt
    tgt.Cells(1, 1).Select
End Sub

Public Sub FitSelected()
Attribute FitSelected.VB_ProcData.VB_Invoke_Func = "K\n14"
    Dim sr As ShapeRange, i As Long, shp As Shape, ws As Worksheet, bc As Long
    Set ws = ActiveSheet
    bc = BoardStartCol(ws)
    If TypeName(Selection) = "Range" Then
        If bc > 0 And ActiveCell.Row >= 2 Then
            RepackRow ws, ActiveCell.Row, bc
        Else
            MsgBox "맞출 그림을 먼저 선택하세요 (Ctrl+클릭으로 여러 개).", vbExclamation
        End If
        Exit Sub
    End If
    On Error Resume Next
    Set sr = Selection.ShapeRange
    On Error GoTo 0
    If sr Is Nothing Then Exit Sub
    For i = 1 To sr.Count
        Set shp = sr.Item(i)
        If bc > 0 Then
            RepackRow ws, CellAtCenter(shp).Row, bc
        Else
            FitToCell shp, CellAtCenter(shp)
        End If
    Next i
    ActiveCell.Select
End Sub

Public Sub SortByCase()
Attribute SortByCase.VB_ProcData.VB_Invoke_Func = "S\n14"
    Dim ws As Worksheet
    Set ws = ActiveSheet
    If ws.Name <> "Trend" And ws.Name <> "Extra" Then
        MsgBox "'Trend' 또는 'Extra' 시트에서 실행하세요.", vbExclamation: Exit Sub
    End If
    Application.Calculate
    If Not SortSheet(ws) Then MsgBox "'정렬키' 열을 찾을 수 없습니다.", vbExclamation: Exit Sub
    ws.Cells(2, 1).Select
End Sub

Public Sub MergeSites()
Attribute MergeSites.VB_ProcData.VB_Invoke_Func = "U\n14"
    ' 통합 파일에서 실행: IC·CJ 파일의 트렌드·추가확인을 그림까지 다시 불러와 정렬
    Dim wb As Workbook, cfg As Worksheet, paths(1 To 2) As String, i As Long, v As Variant
    Dim src As Workbook, opened As Boolean, sn As Variant, cnt As Long, msg As String
    Set wb = ActiveWorkbook
    On Error Resume Next
    Set cfg = wb.Worksheets("List")
    On Error GoTo 0
    If cfg Is Nothing Then MsgBox "통합 파일에서 실행하세요.", vbExclamation: Exit Sub
    If CStr(cfg.Range("P1").Value) <> "통합 설정" Then
        MsgBox "통합 파일(Defect_Trend_통합.xlsx)에서 실행하세요.", vbExclamation: Exit Sub
    End If
    For i = 1 To 2
        paths(i) = CStr(cfg.Range("Q" & (1 + i)).Value)
        If paths(i) = "" Or Not FileExists(paths(i)) Then
            v = Application.GetOpenFilename("Excel 파일 (*.xlsx;*.xlsm),*.xlsx;*.xlsm", , _
                                            IIf(i = 1, "이천(IC) 파일 선택", "청주(CJ) 파일 선택"))
            If VarType(v) = vbBoolean Then Exit Sub
            paths(i) = CStr(v)
            cfg.Range("Q" & (1 + i)).Value = paths(i)
        End If
    Next i
    If MsgBox("아래 두 파일을 다시 불러와 통합합니다." & vbLf & "(통합 파일의 기존 내용은 지워지고, 원본은 바뀌지 않음)" & vbLf & vbLf & _
              paths(1) & vbLf & paths(2), vbOKCancel + vbQuestion, "통합 갱신") <> vbOK Then Exit Sub

    Application.ScreenUpdating = False
    Application.EnableEvents = False
    Application.Calculation = xlCalculationManual
    On Error GoTo fail
    For Each sn In Array("Trend", "Extra")
        ClearData wb.Worksheets(sn)
    Next sn
    For i = 1 To 2
        Set src = Nothing: opened = False
        On Error Resume Next
        Set src = Workbooks(Mid(paths(i), InStrRev(paths(i), "\") + 1))
        On Error GoTo fail
        If src Is Nothing Then
            Set src = Workbooks.Open(paths(i), UpdateLinks:=0, ReadOnly:=True)
            opened = True
        End If
        For Each sn In Array("Trend", "Extra")
            cnt = AppendSheet(src.Worksheets(sn), wb.Worksheets(sn))
            msg = msg & src.Name & " " & sn & " : " & cnt & "행" & vbLf
        Next sn
        If opened Then src.Close SaveChanges:=False
        wb.Activate
    Next i
    Application.Calculation = xlCalculationAutomatic
    Application.Calculate
    For Each sn In Array("Trend", "Extra")
        SortSheet wb.Worksheets(sn)
    Next sn
    cfg.Range("Q4").Value = Now
    Application.ScreenUpdating = True
    Application.EnableEvents = True
    wb.Worksheets("Brief").Activate
    MsgBox "통합 완료" & vbLf & vbLf & msg & vbLf & "저장(Ctrl+S)하면 반영됩니다.", vbInformation, "통합 갱신"
    Exit Sub
fail:
    Application.Calculation = xlCalculationAutomatic
    Application.ScreenUpdating = True
    Application.EnableEvents = True
    MsgBox "통합 중 오류: " & Err.Description, vbCritical
End Sub

Public Sub DeleteOldPictures()
Attribute DeleteOldPictures.VB_ProcData.VB_Invoke_Func = "D\n14"
    Dim ws As Worksheet, s As String, cutoff As Date, i As Long, cnt As Long, shp As Shape, r As Long
    Set ws = ActiveSheet
    If ws.Name <> "Trend" And ws.Name <> "Extra" Then
        MsgBox "'Trend' 또는 'Extra' 시트에서 실행하세요 (시트마다 따로 실행).", vbExclamation: Exit Sub
    End If
    s = InputBox("확인일이 이 날짜보다 이전인 행의 그림을 삭제합니다." & vbLf & _
                 "먼저 파일 사본(yymm_보관.xlsx)을 저장했는지 확인하세요." & vbLf & vbLf & _
                 "기준일 (예: 2026-09-01):", "오래된 그림 삭제", Format(Date - 90, "yyyy-mm-dd"))
    If s = "" Then Exit Sub
    If Not IsDate(s) Then
        MsgBox "날짜 형식이 아닙니다.", vbExclamation: Exit Sub
    End If
    cutoff = CDate(s)
    For Each shp In ws.Shapes
        If IsOld(ws, shp, cutoff) Then cnt = cnt + 1
    Next shp
    If cnt = 0 Then
        MsgBox "삭제할 그림이 없습니다.", vbInformation: Exit Sub
    End If
    If MsgBox(cnt & "개 그림을 삭제합니다. 텍스트는 그대로 남습니다." & vbLf & "계속할까요?", _
              vbYesNo + vbExclamation, "오래된 그림 삭제") <> vbYes Then Exit Sub
    For i = ws.Shapes.Count To 1 Step -1
        Set shp = ws.Shapes(i)
        If IsOld(ws, shp, cutoff) Then
            r = CellAtCenter(shp).Row
            shp.Delete
            ws.Rows(r).RowHeight = 45
        End If
    Next i
    MsgBox cnt & "개 삭제 완료. 저장하면 파일 용량이 줄어듭니다.", vbInformation
End Sub

' ---------------------------------------------------------------- 내부 함수
Private Function ClipHasPicture() As Boolean
    Dim f As Variant
    For Each f In Application.ClipboardFormats
        If f = xlClipboardFormatBitmap Or f = xlClipboardFormatPICT Or f = 14 Then
            ClipHasPicture = True: Exit Function
        End If
    Next f
End Function

Private Function TryPaste(ws As Worksheet, n As Long) As Boolean
    Dim fmts As Variant, i As Long
    fmts = Array("그림 (JPEG)", "그림(JPEG)", "Picture (JPEG)", "그림 (PNG)", "그림(PNG)", "Picture (PNG)")
    On Error Resume Next
    For i = LBound(fmts) To UBound(fmts)
        Err.Clear
        ws.PasteSpecial Format:=fmts(i), Link:=False, DisplayAsIcon:=False
        If Err.Number = 0 And ws.Shapes.Count > n Then TryPaste = True: Exit Function
    Next i
    Err.Clear
    ws.Pictures.Paste
    TryPaste = (Err.Number = 0 And ws.Shapes.Count > n)
    On Error GoTo 0
End Function

Private Sub FitToCell(shp As Shape, c As Range)
    Dim w As Double, h As Double
    w = c.Width - 2 * MARGIN: h = c.Height - 2 * MARGIN
    If w <= 0 Or h <= 0 Then Exit Sub
    shp.LockAspectRatio = msoTrue
    If shp.Width / shp.Height > w / h Then
        shp.Width = w
    Else
        shp.Height = h
    End If
    shp.Left = c.Left + (c.Width - shp.Width) / 2
    shp.Top = c.Top + (c.Height - shp.Height) / 2
    shp.Placement = xlMoveAndSize
End Sub

Private Function CellAtCenter(shp As Shape) As Range
    Dim cx As Double, cy As Double, c As Range
    cx = shp.Left + shp.Width / 2: cy = shp.Top + shp.Height / 2
    Set c = shp.TopLeftCell
    Do While c.Left + c.Width < cx: Set c = c.Offset(0, 1): Loop
    Do While c.Top + c.Height < cy: Set c = c.Offset(1, 0): Loop
    Set CellAtCenter = c.MergeArea
End Function

Private Function IsOld(ws As Worksheet, shp As Shape, cutoff As Date) As Boolean
    Dim r As Long, v As Variant
    If shp.Type <> msoPicture And shp.Type <> msoLinkedPicture Then Exit Function
    r = CellAtCenter(shp).Row
    If r < 2 Then Exit Function
    v = ws.Cells(r, 2).Value
    If IsDate(v) Then IsOld = (CDate(v) < cutoff)
End Function

' ---------------------------------------------------------------- 추가확인 시트용
Private Function BoardStartCol(ws As Worksheet) As Long
    Dim i As Long, v As Variant
    For i = 1 To 60
        v = ws.Cells(1, i).Value
        If Not IsError(v) Then
            If Left(CStr(v), 3) = "이미지" Then BoardStartCol = i: Exit Function
        End If
    Next i
End Function

Private Function InRow(shp As Shape, ws As Worksheet, r As Long) As Boolean
    Dim cy As Double
    cy = shp.Top + shp.Height / 2
    InRow = (cy >= ws.Rows(r).Top And cy < ws.Rows(r).Top + ws.Rows(r).Height)
End Function

Private Function RowRightEdge(ws As Worksheet, r As Long, bc As Long, excludeName As String) As Double
    Dim x As Double, shp As Shape, x0 As Double
    x0 = ws.Cells(r, bc).Left
    x = x0 + GAP
    For Each shp In ws.Shapes
        If shp.Name <> excludeName And shp.Type = msoPicture Then
            If shp.Left >= x0 - 1 Then
                If InRow(shp, ws, r) Then
                    If shp.Left + shp.Width + GAP > x Then x = shp.Left + shp.Width + GAP
                End If
            End If
        End If
    Next shp
    RowRightEdge = x
End Function

Private Sub PlaceInRow(shp As Shape, ws As Worksheet, r As Long, x As Double)
    Dim h As Double
    h = ws.Rows(r).Height - 2 * (MARGIN + 2)
    If h <= 0 Then Exit Sub
    shp.LockAspectRatio = msoTrue
    shp.Height = h
    shp.Top = ws.Rows(r).Top + (ws.Rows(r).Height - shp.Height) / 2
    shp.Left = x
    shp.Placement = xlMoveAndSize
End Sub

Private Sub RepackRow(ws As Worksheet, r As Long, bc As Long)
    Dim arr() As Shape, n As Long, shp As Shape, i As Long, j As Long, tmp As Shape, x As Double, x0 As Double
    x0 = ws.Cells(r, bc).Left
    ReDim arr(1 To ws.Shapes.Count + 1)
    For Each shp In ws.Shapes
        If shp.Type = msoPicture Then
            If shp.Left + shp.Width > x0 And InRow(shp, ws, r) Then
                n = n + 1: Set arr(n) = shp
            End If
        End If
    Next shp
    If n = 0 Then Exit Sub
    For i = 1 To n - 1
        For j = i + 1 To n
            If arr(j).Left < arr(i).Left Then Set tmp = arr(i): Set arr(i) = arr(j): Set arr(j) = tmp
        Next j
    Next i
    x = x0 + GAP
    For i = 1 To n
        PlaceInRow arr(i), ws, r, x
        x = x + arr(i).Width + GAP
    Next i
End Sub

' ---------------------------------------------------------------- 정렬 · 통합용
Private Function HeaderCol(ws As Worksheet, title As String) As Long
    Dim f As Range
    Set f = ws.Rows(1).Find(What:=title, LookIn:=xlValues, LookAt:=xlWhole)
    If Not f Is Nothing Then HeaderCol = f.Column
End Function

Private Function LastDataRow(ws As Worksheet) As Long
    LastDataRow = Application.WorksheetFunction.Max(ws.Cells(ws.Rows.Count, 2).End(xlUp).Row, _
                                                    ws.Cells(ws.Rows.Count, 3).End(xlUp).Row, 1)
End Function

Private Function SortSheet(ws As Worksheet) As Boolean
    Dim keyCol As Long, lastR As Long
    keyCol = HeaderCol(ws, "정렬키")
    If keyCol = 0 Then Exit Function
    SortSheet = True
    lastR = LastDataRow(ws)
    If lastR < 3 Then Exit Function
    If ws.FilterMode Then ws.ShowAllData
    With ws.Sort
        .SortFields.Clear
        .SortFields.Add Key:=ws.Range(ws.Cells(2, keyCol), ws.Cells(lastR, keyCol)), _
                        SortOn:=xlSortOnValues, Order:=xlAscending
        .SetRange ws.Range(ws.Cells(2, 1), ws.Cells(lastR, keyCol))
        .Header = xlNo
        .Orientation = xlTopToBottom
        .Apply
    End With
End Function

Private Function FileExists(p As String) As Boolean
    On Error Resume Next
    FileExists = (Len(Dir(p)) > 0)
End Function

Private Sub ClearData(ws As Worksheet)
    ' 통합 파일 데이터 초기화: 그림 삭제 + 입력 칸 비우기 (수식 칸은 유지)
    Dim lastR As Long, keyCol As Long, c As Long, i As Long, h As Double
    keyCol = HeaderCol(ws, "정렬키")
    lastR = LastDataRow(ws)
    For i = ws.Shapes.Count To 1 Step -1
        If ws.Shapes(i).Type = msoPicture Then
            If ws.Shapes(i).TopLeftCell.Row >= 2 Then ws.Shapes(i).Delete
        End If
    Next i
    If ws.FilterMode Then ws.ShowAllData
    If lastR < 2 Then Exit Sub
    h = ws.Rows(lastR + 1).Height
    For c = 1 To keyCol
        If IsInputCol(ws, c) Then ws.Range(ws.Cells(2, c), ws.Cells(lastR, c)).ClearContents
    Next c
    ws.Range(ws.Rows(2), ws.Rows(lastR)).RowHeight = h
End Sub

Private Function AppendSheet(src As Worksheet, dst As Worksheet) As Long
    ' src의 데이터 행(입력 칸 값 + 그림)을 dst의 다음 빈 행부터 복사. 복사한 행 수 반환
    Dim keyCol As Long, srcLast As Long, d As Long, r As Long, c As Long
    Dim mp() As Long, shp As Shape, ns As Shape, sr As Long, n As Long
    keyCol = HeaderCol(dst, "정렬키")
    srcLast = LastDataRow(src)
    If srcLast < 2 Then Exit Function
    d = LastDataRow(dst) + 1
    ReDim mp(1 To srcLast)
    For r = 2 To srcLast
        If CStr(src.Cells(r, 2).Value) <> "" Or CStr(src.Cells(r, 3).Value) <> "" Then
            If Not dst.Cells(d, 1).HasFormula Then
                Err.Raise vbObjectError + 1, , "통합 파일의 수식 행이 부족합니다 (" & dst.Name & " " & d & "행)."
            End If
            For c = 1 To keyCol
                If IsInputCol(dst, c) Then
                    If Not IsEmpty(src.Cells(r, c).Value) Then dst.Cells(d, c).Value = src.Cells(r, c).Value
                End If
            Next c
            dst.Rows(d).RowHeight = src.Rows(r).Height
            mp(r) = d
            d = d + 1: n = n + 1
        End If
    Next r
    dst.Parent.Activate
    dst.Activate
    For Each shp In src.Shapes
        If shp.Type = msoPicture Then
            sr = CellAtCenter(shp).Row
            If sr >= 2 And sr <= srcLast Then
                If mp(sr) > 0 Then
                    shp.Copy
                    dst.Cells(mp(sr), 1).Select
                    dst.Paste
                    Set ns = dst.Shapes(dst.Shapes.Count)
                    ns.LockAspectRatio = msoFalse
                    ns.Width = shp.Width: ns.Height = shp.Height
                    ns.Left = shp.Left
                    ns.Top = dst.Rows(mp(sr)).Top + (shp.Top - src.Rows(sr).Top)
                    ns.LockAspectRatio = msoTrue
                    ns.Placement = xlMoveAndSize
                End If
            End If
        End If
    Next shp
    AppendSheet = n
End Function

Private Function IsInputCol(ws As Worksheet, c As Long) As Boolean
    ' 입력 열 = 1행 헤더 색이 E7E6E6(진한 회색). 수식 열·그림 열은 제외
    IsInputCol = (ws.Cells(1, c).Interior.Color = RGB(231, 230, 230))
End Function
