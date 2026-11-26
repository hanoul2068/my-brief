Attribute VB_Name = "DefectTrend"
Option Explicit
' Defect Trend 로그용 그림 매크로 (개인용 매크로 통합 문서 PERSONAL.XLSB에 넣어 사용)
'   Ctrl+Shift+J : 복사한 그림을 JPEG로 붙여넣기
'                  - 트렌드 시트 : 선택한 칸 크기에 맞춤
'                  - 추가확인 시트 : 그 행의 마지막 그림 오른쪽에 행 높이로 이어 붙임
'   Ctrl+Shift+K : 그림 정리
'                  - 트렌드 시트 : 선택한 그림(여러 개 가능)을 각자 놓인 칸에 맞춤
'                  - 추가확인 시트 : 선택한 그림(또는 선택한 칸)이 있는 행의 그림을 왼쪽부터 다시 정렬
'   Ctrl+Shift+S : '트렌드' / '추가확인' 시트를 Case별로 정렬 (Case 발견순 -> 날짜순, 그림도 같이 이동)
'   Ctrl+Shift+D : '트렌드' / '추가확인' 시트에서 기준일 이전 행의 그림만 삭제 (텍스트는 유지)

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
    Dim ws As Worksheet, keyCol As Long, lastR As Long, f As Range
    Set ws = ActiveSheet
    If ws.Name <> "트렌드" And ws.Name <> "추가확인" Then
        MsgBox "'트렌드' 또는 '추가확인' 시트에서 실행하세요.", vbExclamation: Exit Sub
    End If
    Set f = ws.Rows(1).Find(What:="정렬키", LookIn:=xlValues, LookAt:=xlWhole)
    If f Is Nothing Then
        MsgBox "'정렬키' 열을 찾을 수 없습니다.", vbExclamation: Exit Sub
    End If
    keyCol = f.Column
    lastR = Application.WorksheetFunction.Max(ws.Cells(ws.Rows.Count, 2).End(xlUp).Row, _
                                              ws.Cells(ws.Rows.Count, 3).End(xlUp).Row)
    If lastR < 3 Then Exit Sub
    If ws.FilterMode Then ws.ShowAllData
    Application.Calculate
    With ws.Sort
        .SortFields.Clear
        .SortFields.Add Key:=ws.Range(ws.Cells(2, keyCol), ws.Cells(lastR, keyCol)), _
                        SortOn:=xlSortOnValues, Order:=xlAscending
        .SetRange ws.Range(ws.Cells(2, 1), ws.Cells(lastR, keyCol))
        .Header = xlNo
        .Orientation = xlTopToBottom
        .Apply
    End With
    ws.Cells(2, 1).Select
End Sub

Public Sub DeleteOldPictures()
Attribute DeleteOldPictures.VB_ProcData.VB_Invoke_Func = "D\n14"
    Dim ws As Worksheet, s As String, cutoff As Date, i As Long, cnt As Long, shp As Shape, r As Long
    Set ws = ActiveSheet
    If ws.Name <> "트렌드" And ws.Name <> "추가확인" Then
        MsgBox "'트렌드' 또는 '추가확인' 시트에서 실행하세요 (시트마다 따로 실행).", vbExclamation: Exit Sub
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
