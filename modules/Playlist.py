import os
import requests
from modules.Song import Song
from util.outputManager import ensureDirectoryExists


class Playlist:
  id = ""
  name = ""
  playlistSongs = None
  imgUrl = ""
  
  def __init__(self, name, id):
    self.id = id
    self.name = name \
      .replace('\\', ' ') \
      .replace('/', ' ') \
      .replace('?', ' ')
    self.playlistSongs = []
  
  @staticmethod
  def fromSpotify(apiObj, downloaderSongs, sp):
    playlistObj = Playlist(apiObj['name'], apiObj['id'])

    if 'images' in apiObj and apiObj['images'] is not None and len(apiObj['images']) > 0:
      playlistObj.imgUrl = apiObj['images'][0]['url']
      
    offset = 0
    playlistTracks = sp.playlist_items(apiObj['id'])

    while len(playlistTracks['items']) > 0:
      for t in playlistTracks['items']:
        if (not 'track' in t) or (t['track'] == None):
          continue
  
        track = t['track']
  
        if track['id'] in downloaderSongs:
          song = downloaderSongs[track['id']]
        else:
          song = Song.fromApiObj(track)
    
          if song == None:
            continue
        
        playlistObj.playlistSongs.append(song)
        
      offset += len(playlistTracks['items'])
      playlistTracks = sp.playlist_items(apiObj['id'], offset=offset)
    return playlistObj
  def getFileName(self, includeExtension=True):
    return self.name \
      .replace("<", "") \
      .replace(">", "") \
      .replace("\\", "") \
      .replace("/", "") \
      + (".m3u" if includeExtension else "")
  
  def saveToFile(self, outputDir):
    fileStr = "#EXTM3U\n\n"
    fileStr += f"#PLAYLIST:{self.name}\n\n"
    
    try:
      cover_data = requests.get(self.imgUrl).content
      coverImgName = os.path.join('coverImages', self.getFileName(False) + ".jpg")
      coverImgLoc = os.path.join(outputDir, coverImgName)
      
      coverImgDirExists, coverImgDir = ensureDirectoryExists(os.path.split(coverImgLoc)[0], outputDir)
      
      with open(str(coverImgLoc), mode='wb') as f:
        f.write(cover_data)
      
      fileStr += f"EXTIMG:{coverImgName}"
    except:
      pass
    
    for song in self.playlistSongs:
      fileStr += song.getM3uLine()
    
    with open(os.path.join(outputDir, self.getFileName()), 'w', encoding="utf-8") as f:
      f.write(fileStr)