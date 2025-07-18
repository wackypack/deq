import tkinter as tk
from tkinter import filedialog, messagebox
import os
from os import listdir, getcwd, makedirs
from os.path import isfile, isdir, join, dirname, basename, exists
import wave
import string
import struct

def acidize(filename, rootKey, loopStart, loopEnd, detune):
    wavFinal=open(fname,"r+b")
    wavFinal.seek(0, 2)

    sampRootKey=struct.pack('<B', rootKey)
    sampLoopStart=struct.pack('<L', loopStart)
    if loopEnd<=1:
        sampLoopEnd=struct.pack('<L', 0)
    else:
        sampLoopEnd=struct.pack('<L', loopEnd-1)
    sampDetune = struct.pack('<l', detune) if pitchMode == 1 else struct.pack('<L', detune)

    wavFinal.write(b"smpl\x3c\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x61\x51\x00\x00"+sampRootKey+b"\x00\x00\x00"+sampDetune+b"\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"+sampLoopStart+sampLoopEnd+b"\x00\x00\x00\x00\x00\x00\x00\x00")
    wavFinal.seek(4)
    riffSize=int.from_bytes(wavFinal.read(4), "little")
    riffSize+=68
    wavFinal.seek(4)
    wavFinal.write(struct.pack('<L', riffSize))

    wavFinal.close()

def voiceInfo(group,name,rgnCount,rgnSplits,velCount,veloSplits,roots,tunes,names):
    text = "%s:%s\n\n" % (group,name)
    rgnInfo="Key Ranges:\n"
    velInfo="Velocity Ranges:\n"
    smpInfo="Samples:\n"
    
    lower = 0
    if velCount > 1:
        for n in range(velCount):
            velInfo = velInfo + "\t%s: %s - %s\n" % (str(n), str(lower), str(veloSplits[n]))
            lower = veloSplits[n] + 1
        text = text + velInfo + "\n"
    
    lower = 0
    for n in range(rgnCount):
        rgnInfo = rgnInfo + "\t%s: %s - %s\n" % (str(n), str(lower), str(rgnSplits[n]))
        lower = rgnSplits[n] + 1
    text = text + rgnInfo + "\n"

    for r in range(rgnCount):
        for v in range(velCount):
            semitones = round(tunes[(r*velCount)+v]*(50/128))
            if semitones > 0:
                semitones = "+" + str(semitones)
            else:
                semitones = str(semitones)
            if velCount > 1:
                smpInfo = smpInfo + "\tRegion %s velocity %s:\n" % (str(r), str(v))
            else:
                smpInfo = smpInfo + "\tRegion %s:\n" % str(r)
            smpInfo = smpInfo + "\t\tSample Name: %s\n" % names[(r*velCount)+v]
            smpInfo = smpInfo + "\t\tRoot:        %s\n" % roots[(r*velCount)+v]
            smpInfo = smpInfo + "\t\tDetune:      %s (%s cents)\n" % (tunes[(r*velCount)+v], semitones)
        if r != rgnCount-1:
            smpInfo = smpInfo + "\t%s\n" % (" -"*6)
    text = text + smpInfo + "\n%s\n\n" % ("-"*20)
    
    return text

root = tk.Tk()
root.withdraw()

print("DeQ v.1 by floomatic labs\n")

print("Please open an Alesis Q-Card or QuadraCard .img file...")

filePath=filedialog.askopenfilename()
file=open(filePath, mode="rb")
size=os.path.getsize(filePath)
outPath=dirname(filePath)
bname=basename(filePath)

file.seek(65536)
if file.read(4) == b"\x00\x70\x38\x1C":
    print("Sound block detected at 0x10000")
    beginoffs=65536
else:
    beginoffs=int(input("Sound block not found, enter address (in dec) to rip from it manually.\n(Sound block header in hex: 00 70 38 1C)"))

# beginoffs=int(input("\ninput offset to begin ripping samples from\n(in dec, seems to always be 65560): "))
file.seek(beginoffs+10)
romName = file.read(14).decode("utf-8").rstrip().replace("/","-")
print("Sound block name: %s" % romName)
if not exists(join(outPath,romName)):
    makedirs(join(outPath,romName))
outPath = join(outPath,romName)
#ignoreDupes = True if input("\nignore duplicates?\n(this will interfere with exporting drum mode voices, should you choose to)\n(y/n): ").lower() == "y" else False
#ignoreVelPgms = True if input("\nignore velocity-sensitive voices?\n(y/n): ").lower() == "y" else False
#ignorePercussion = True if input("\nignore drum mode voices?\n(most of these are probably duplicates of the standard keymaps, fyi)\n(y/n): ").lower() == "y" else False

pitchMode = int(input("Please specify which mode to use to store pitch correction parameters in samples.\n(0 = normal unsigned, 1 = signed, Polyphone compatible): "))

ignoreDupes = True
ignoreVelPgms = False
ignorePercussion = False

if not ignorePercussion and not exists(outPath+"/drum"):
    makedirs(outPath+"/drum")

keymapMelodicCount=0
paramAddress=beginoffs

seek=beginoffs+24
currSmp=0
file.seek(beginoffs+24)

voiceGroupNames=[]
drumGroupNames=[]
for x in range(8):
    voiceGroupNames.append(file.read(6).decode("utf-8").rstrip().replace("/","-"))
for x in range(6):
    drumGroupNames.append(file.read(6).decode("utf-8").rstrip().replace("/","-"))

paramAddress=file.tell()

waveforms={}

keymapInfo=""

while seek<size:
    file.seek(paramAddress)
    keymapType=int.from_bytes(file.read(1),"big")
    if keymapType in (16,17,18,19,20,21,22,23,55,56,57,58,59,60):
        keymapIndex=int.from_bytes(file.read(1),"big")
        keymapName=file.read(10).decode("utf-8").rstrip().replace("/","-")
        groupName=voiceGroupNames[keymapType-16] if keymapType < 24 else "drum/"+drumGroupNames[keymapType-55]
        regionCount=int.from_bytes(file.read(1),"big")+1
        velRegionCount=int.from_bytes(file.read(1),"big")+1
        velSplit1=int.from_bytes(file.read(1),"big")
        velSplit2=int.from_bytes(file.read(1),"big")
        velSplits=(velSplit1,velSplit2,127)
        print("%s:%s (%s regions)" % (groupName, keymapName, str(regionCount)))
        regionsLen=-(-regionCount//2)*2
        regions = file.read(regionsLen)

        # stuff to fill out region info
        regionSplits = []
        for n in range(regionCount):
            regionSplits.append(regions[n])
        rootNotes=[]
        detunes=[]
        waveNames=[]
        
        for r in range(regionCount):
            for v in range(velRegionCount):
                waveRootKey=int.from_bytes(file.read(1),"big")
                waveFineTune=int.from_bytes(file.read(1),"big")

                if pitchMode == 0:
                    if waveFineTune > 0:
                        waveRootKey += 1
                        waveFineTune = -waveFineTune + 255
                else:
                    if waveFineTune >= 128:
                        waveRootKey += 1
                        waveFineTune = -waveFineTune + 255
                    else:
                        waveFineTune = -waveFineTune
                file.seek(file.tell()+1)
                waveVolume=int.from_bytes(file.read(1),"big")
                wLoopHi=int.to_bytes(waveVolume%4,1,"big")
                wLoopLo=file.read(2)
                waveLoopFrame=int.from_bytes(wLoopHi+wLoopLo,"big")
                waveVolume=waveVolume//4
                wEndLo=file.read(2)
                wEndHi=file.read(1)
                wStartHi=file.read(1)
                wStartLo=file.read(2)
                waveEndFrame=int.from_bytes(wEndHi+wEndLo,"big")
                waveStartFrame=int.from_bytes(wStartHi+wStartLo,"big")
                if waveStartFrame >= 8388608:
                    waveStartFrame -= 8388608
                if waveEndFrame >= 8388608:
                    waveEndFrame -= 8388608    
                #print("root key: %s" % str(waveRootKey))
                #print("fine tune: %s" % str(waveFineTune))
                #print("volume: %s" % str(waveVolume))
                #print("loop start: %s" % str(waveLoopFrame))
                #print("wave begin: %s" % str(waveStartFrame))
                #print("wave end: %s" % str(waveEndFrame))

                rootNotes.append(waveRootKey)
                detunes.append(waveFineTune)

                paramAddress=file.tell()

                if (waveStartFrame,waveEndFrame,waveLoopFrame) in waveforms:
                    waveNames.append(waveforms[(waveStartFrame,waveEndFrame,waveLoopFrame)])
                
                if (velRegionCount>1 and ignoreVelPgms) or (keymapType > 24 and ignorePercussion) or ((waveStartFrame,waveEndFrame,waveLoopFrame) in waveforms and ignoreDupes):
                    pass
                else:
                    print("Exporting waveform %s/%s" % (str(v*regionCount+r), str(regionCount*velRegionCount)), end="\r")
                    file.seek(waveStartFrame*2)
                    waveLength=(waveEndFrame-waveStartFrame+1)*2
                    waveData=file.read(waveLength)
                    waveDataLittle=waveData[1::-1]
                    for f in range((waveLength//2)-1):
                        e=(f*2)+3
                        s=(f*2)+1
                        waveDataLittle=waveDataLittle+waveData[e:s:-1]

                    if velRegionCount > 1:
                        waveName="%s_%s_%s_v%s" % ( groupName, keymapName, str(r), velSplits[v])
                    else:
                        waveName="%s_%s_%s" % (groupName, keymapName, str(r))

                    waveNames.append(waveName)

                    fname=outPath+"/%s.wav" % waveName
                    
                    wavOut = wave.open(fname,"w")
                    wavOut.setnchannels(1)
                    wavOut.setsampwidth(2)
                    wavOut.setframerate(48000)
                    wavOut.writeframesraw(waveDataLittle)
                    wavOut.close()

                    acidize(fname, waveRootKey, waveLoopFrame, (waveLength//2)-1, waveFineTune*(2**24))

                    waveforms[(waveStartFrame,waveEndFrame,waveLoopFrame)] = waveName

                    # waveforms.append((waveStartFrame,waveEndFrame,waveLoopFrame))

                    file.seek(paramAddress)
        
        keymapInfo = keymapInfo + voiceInfo(groupName,keymapName,regionCount,regionSplits,velRegionCount,velSplits,rootNotes,detunes,waveNames)
    else:
        keymapInfo = ("Alesis Q-Card: %s\n\n" % romName) + keymapInfo
        regionsInfo=open(outPath+"/Regions.txt","w")
        regionsInfo.write(keymapInfo)
        regionsInfo.close()
        input("Finished processing.\nPress Enter to exit.")
        os._exit(0)
            
    
