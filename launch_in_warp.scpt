on run argv
    set commandToRun to item 1 of argv
    
    tell application "Warp"
        activate
        
        -- Wait for Warp to become active
        delay 0.5
        
        -- Try to create a new tab using keyboard shortcut
        tell application "System Events"
            keystroke "t" using {command down}
        end tell
        
        -- Wait for the new tab to be ready
        delay 0.5
        
        -- Execute the command
        tell application "System Events"
            keystroke commandToRun
            keystroke return
        end tell
    end tell
end run

