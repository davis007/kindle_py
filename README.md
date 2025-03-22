# KindleReader起動アプリケーション作成ガイド

このドキュメントでは、Macの「Automator」アプリケーションを使用して、kindleReaderスクリプトを起動するカスタムアプリケーションを作成する方法を説明します。このアプリケーションは、ダブルクリックするだけでWarpターミナルでkindleReaderを起動できます。

## 必要なもの

- macOS（Catalina以降推奨）
- Automatorアプリケーション（macOSに標準搭載）
- Warpターミナルアプリケーション（インストール済み）
- kindleReaderスクリプト（実行権限があること）

## Automatorでアプリケーションを作成する手順

1. **Automatorを起動する**
   - Finderで「アプリケーション」フォルダを開き、「Automator」をダブルクリックします。
   - または、Spotlightで「Automator」と検索して起動します。

2. **新規ドキュメントを作成する**
   - 「新規書類」ダイアログが表示されたら、「アプリケーション」を選択して「選択」をクリックします。
   
3. **アクションを追加する**
   - 左側のライブラリから「ユーティリティ」を選択します。
   - 「AppleScriptを実行」アクションを見つけて、右側のワークフローエリアにドラッグ＆ドロップします。

4. **AppleScriptコードを入力する**
   - 「AppleScriptを実行」アクションのテキストエリアに、以下のAppleScriptコードを入力します。
   - kindleReaderスクリプトのパスは実際の環境に合わせて変更してください。

## 必要なAppleScriptコード

以下のコードを「AppleScriptを実行」アクションに貼り付けます：

```applescript
on run {input, parameters}
    -- kindleReaderスクリプトのフルパス（実際のパスに変更してください）
    set kindleReaderPath to "/Volumes/ARSTH-2TB/dev/new_py_kindle/kindleReader"
    
    -- Warpが実行中かどうかを確認
    tell application "System Events"
        set isWarpRunning to (exists (processes where name is "Warp"))
    end tell
    
    -- Warpが実行中でない場合は起動
    if not isWarpRunning then
        tell application "Warp" to activate
        delay 1 -- Warpが起動するまで少し待つ
    end if
    
    -- Warpをアクティブにし、新しいタブを開く
    tell application "Warp" to activate
    tell application "System Events"
        tell process "Warp"
            -- Command+Tを押して新しいタブを開く
            keystroke "t" using command down
            delay 0.5 -- タブが開くまで少し待つ
            
            -- kindleReaderスクリプトを実行
            keystroke kindleReaderPath
            keystroke return
        end tell
    end tell
    
    return input
end run
```

## アプリケーションの保存方法

1. **アプリケーションを保存する**
   - メニューから「ファイル」→「保存」を選択します。
   - ファイル名を「KindleReaderLauncher」などのわかりやすい名前にします。
   - 保存先として「アプリケーション」フォルダを選択するか、任意の場所を選びます。
   - 「ファイルフォーマット」が「アプリケーション」になっていることを確認します。
   - 「保存」ボタンをクリックします。

2. **アプリケーションアイコンを変更する（オプション）**
   - 任意のアイコンファイル（.icns）を用意します。
   - Finderで作成したアプリケーションを右クリックし、「情報を見る」を選択します。
   - 左上のアイコンをクリックし、「編集」→「ペースト」でアイコンを変更できます。

## アプリケーションの使用方法

1. **アプリケーションを起動する**
   - Finderで保存したアプリケーション（KindleReaderLauncher.app）をダブルクリックします。
   - 初回実行時は、セキュリティ警告が表示される場合があります。その場合は「開く」をクリックします。
   - 初回実行時、アクセシビリティの許可を求められるダイアログが表示されたら、許可してください。

2. **自動実行の流れ**
   - アプリケーションが起動すると、自動的に次の処理が行われます：
     - Warpターミナルが起動（または最前面に表示）
     - 新しいタブが開かれる
     - kindleReaderスクリプトが実行される

## トラブルシューティングのヒント

1. **アプリケーションが起動しない場合**
   - システム環境設定の「セキュリティとプライバシー」で、「ダウンロードしたアプリケーションの実行許可」が適切に設定されているか確認してください。
   - 「一般」タブで「このまま開く」を選択する必要があるかもしれません。

2. **アクセシビリティの許可が必要な場合**
   - システム環境設定の「セキュリティとプライバシー」→「プライバシー」→「アクセシビリティ」で、作成したアプリケーションにチェックが入っているか確認してください。
   - チェックが入っていない場合は、左下の「+」ボタンをクリックして、作成したアプリケーションを追加してください。

3. **Warpが正しく起動しない場合**
   - AppleScriptコード内の「Warp」の名前が、インストールされているアプリケーションの正確な名前と一致しているか確認してください。
   - delay値（0.5秒や1秒）を増やして、各動作の間の待ち時間を長くしてみてください。

4. **kindleReaderスクリプトが見つからない場合**
   - AppleScriptコード内の`kindleReaderPath`変数が、kindleReaderスクリプトの正確な絶対パスを指しているか確認してください。
   - スクリプトに実行権限があることを確認してください（ターミナルで`chmod +x kindleReader`を実行）。

5. **コマンドが入力されない場合**
   - システムの動作が遅い場合は、delayの値（waitの秒数）を調整して、各ステップ間の待ち時間を長くしてみてください。

## 注意事項

- このアプリケーションは、AppleScriptを使用してキーボード入力をシミュレートしているため、実行中はキーボードやマウスを操作しないでください。
- macOSのアップデートにより、セキュリティ設定や権限の要件が変更される場合があります。最新のmacOSバージョンに合わせて手順を調整してください。
- kindleReaderスクリプトのパスを変更した場合は、AppleScriptコードも更新する必要があります。

