Attribute VB_Name = "DefectTrend"
Option Explicit
' Defect Trend 로그용 그림 매크로 (개인용 매크로 통합 문서 PERSONAL.XLSB에 넣어 사용)
'   Ctrl+Shift+J : 복사한 그림을 선택한 칸에 JPEG로 붙여넣고 칸 크기에 맞춤
'   Ctrl+Shift+K : 선택한 그림(여러 개 가능)을 각자 놓인 칸에 맞춤
'   Ctrl+Shift+D : '트렌드' 시트에서 기준일 이전 행의 그림만 삭제 (텍스트는 유지)

Private Const MARGIN As Double = 2   ' 칸 안쪽 여백 (pt)

Public Sub PasteFit()
Attribute PasteFit.VB_ProcData.VB_Invoke_Func = "J\n14"
    Dim ws As Worksheet, tgt As Range, n As Long
    If TypeName(Selection) <> "Range" Then
        MsgBox "그림을 넣을 칸을 먼저 클릭하세요.", vbExclamation: Exit Sub
    End If
    If Not ClipHasPicture() Then
        MsgBox "복사된 그림이 없습니다. 캡처/그림을 복사한 뒤 다시 실행하세요.", vbExclamation: Exit Sub
    End If
    Set ws = ActiveSheet
    Set tgt = ActiveCell.MergeArea
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
    Dim sr As ShapeRange, i As Long, shp As Shape
    If TypeName(Selection) = "Range" Then
        MsgBox "맞출 그림을 먼저 선택하세요 (Ctrl+클릭으로 여러 개).", vbExclamation: Exit Sub
    End If
    On Error Resume Next
    Set sr = Selection.ShapeRange
    On Error GoTo 0
    If sr Is Nothing Then Exit Sub
    For i = 1 To sr.Count
        Set shp = sr.Item(i)
        FitToCell shp, CellAtCenter(shp)
    Next i
    ActiveCell.Select
End Sub

Public Sub DeleteOldPictures()
Attribute DeleteOldPictures.VB_ProcData.VB_Invoke_Func = "D\n14"
    Dim ws As Worksheet, s As String, cutoff As Date, i As Long, cnt As Long, shp As Shape, r As Long
    Set ws = ActiveSheet
    If ws.Name <> "트렌드" Then
        MsgBox "'트렌드' 시트에서 실행하세요.", vbExclamation: Exit Sub
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
