function WriteFile()
    -- Debug: show that Lua ran
   -- SKIN:Bang('!SetOption MeterDebug Text "Lua ran"')
   -- SKIN:Bang('!UpdateMeter MeterDebug')
   -- SKIN:Bang('!Redraw')

    -- Grab Title and Artist directly
    local title = SKIN:GetMeasure("MeasureTitle"):GetStringValue()
    local artist = SKIN:GetMeasure("MeasureArtist"):GetStringValue()

    -- Handle empty values gracefully
    if title == "" then title = "N/A" end
    if artist == "" then artist = "N/A" end

    local track = title .. " - " .. artist

    -- Write to NowPlaying.txt in @Resources
    local file = io.open(SKIN:GetVariable("@").."NowPlaying.txt", "w")
    if file then
        file:write(track)
        file:close()
    else
        SKIN:Bang('!SetOption MeterDebug Text "File open failed"')
        SKIN:Bang('!UpdateMeter MeterDebug')
        SKIN:Bang('!Redraw')
    end
end
