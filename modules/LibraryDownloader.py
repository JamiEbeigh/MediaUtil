import os
import sys
import requests
import asyncio
from util import CredentialsManager
from util.decorators import background
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from util.outputManager import printProgress
import util.modules.youtubesearchpython as yts
import youtube_dl
import yt_dlp
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3, APIC, TRCK
from datetime import datetime as dt

class Downloader:
  '''
  Download your full spotify library
  '''

  _ClientId = ""
  _ClientSecret = ""
  _OutputDir = ""
  _RedirectUri = "http://localhost:8080"
  _Scope = "user-library-read playlist-read-private"
  _options = None
  _spCurrentUser = ""
  _totalCollected = 0
  _totalCollectedAtStart = 0

  playlists = {}
  songs = {}
  songsToDownload = []
  
  def __init__(self, clientId, clientSecret, optionsFile="" ):
    '''
    Initialize a Downloader class

    PARAMETERS:
      clientId - your spotify client id
      clientSecret - your spotify client secret
      optionsFile - a text file containing any optional parameters for this utility
    '''

    # assign private vars
    self._ClientId = clientId
    self._ClientSecret = clientSecret
    self._options = DownloaderOptions(optionsFile)

    # get authenticated spotify client
    self.sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=self._ClientId, client_secret=self._ClientSecret,
                                                        redirect_uri=self._RedirectUri, scope=self._Scope))

    # get the name of the current spotify user
    u = self.sp.current_user()
    self._spCurrentUser = u['display_name']

  def downloadFullLibrary(self, verbose:bool=True, collectPlaylists:bool=True):
    '''
    Download all songs in your spotify library and compile .txt files contating playlist data
    '''

    if collectPlaylists:
      # get user's playlist information via the spotify api
      self._getPlaylistData(verbose)
      
    # get user's "liked songs" via the spotify api
    self._getLibraryData(verbose)

    # search youtube for songs and download them as mp3
    self._downloadAllSongs(verbose)

    if collectPlaylists:
      # save playlists to .txt files
      self._saveAllPlaylists(verbose)
  
  #region downloadSongs
  def _downloadAllSongs(self, verbose=True, parallel=True):
    '''
    iterate through self.songs, search youtube for each song and download it as an .mp3
    '''

    self._totalCollected = len(self.songs) - len(self.songsToDownload)
    self._totalCollectedAtStart = self._totalCollected

    startTime = dt.now()
    tracksDir = os.path.join(self._options.outputDir, "tracks")
    tracksDirExists, trackDir = self._ensureDirectoryExists(tracksDir, self._options.outputDir)

    if verbose: verbose = printProgress("Downloading Songs", self._totalCollected, len(self.songs), startTime,
                                        startAmount=len(self.songs) - len(self.songsToDownload))
    if not tracksDirExists:
      return
    
    if parallel:
      loop = asyncio.get_event_loop()  # Have a new event loop
      looper = asyncio.gather(*[self._downloadOneSongAsync(s, startTime) for s in self.songsToDownload])  # Run the loop
      loop.run_until_complete(looper)
    else:
      for s in self.songsToDownload:
        self._downloadOneSong(s)

    self._saveFailedSongs()
    self._serializeSongsFile(os.path.join(self._options.outputDir, ".data", "songs.txt"))

  @background
  def _downloadOneSongAsync( self, song, startTime=None ):
    return self._downloadOneSong(song, startTime)
    
  def _downloadOneSong(self, song, startTime=None):
    '''
    search youtube for a song and download the audio

    PARAMETERS:
      track - the spotify object for the song
      alreadyDownloaded - a list of "<artist> - <song title>" containing the songs which have already been downloaded
    '''

    # set the file name to <artist> - <title> but don't append the '.mp3' yet
    fileName = song.getSaveLoc(self._options.outputDir)
    albumDir = os.path.split(fileName)[0]
    albumDirExists, albumDir = self._ensureDirectoryExists(albumDir, self._options.outputDir)

    if not albumDirExists:
      song.error = "Could not create artist/album directory"
      return

    # get find the correct youtube video and find a link 
    ytLink = self._findYoutubeVideo(song.songTitle, song.artist, song.duration)

    if ytLink == None:
      song.error = "Could not find song on YouTube"
      return False

    # download the file and assign a variable to the new location 
    fileLoc = self._downloadFromYoutube(fileName, ytLink)

    if ( fileLoc == "" ):
      song.error = "Error downloading song from YouTube"
      return False
    
    song.fileLoc = os.path.abspath(fileLoc)

    # set ID3/APIC metadata for the file 
    self._setFileMeta(fileLoc, song.songTitle, song.artist, song.album, song.trackNum, song.imgLoc)

    self._totalCollected += 1
    self.songsToDownload.remove(song)
    
    if startTime != None:
      printProgress("Downloading Songs", self._totalCollected, len(self.songs), startTime, startAmount=self._totalCollectedAtStart)

    return True
  #endregion
  
  #region spotify api
  def _getTrackData(self, track):
    '''
    Get a few variables from the track object 

    PARAMETERS:
      track - the spotify object for the song
    RETURNS:
      songTitle - title of the song
      artist - song's artist
      album - album that the song belongs to
      duration - song duration in miliseconds 
      imgLoc - URL where the album cover can be retrieved from
    '''
    
    if track['type'] == 'episode':
      return None, None, None, None, None, None, None

    id = track['id'] \
      .replace('?', '') \
      .replace('/', '') \
      .replace('\\', '') \
      .replace('\'', '') \
      .replace('\"', '') \
      .replace('.', '')

    # get the song title, strip off any special chars
    songTitle = track['name'] \
      .replace('?', '') \
      .replace('/', '') \
      .replace('\\', '') \
      .replace('\'', '') \
      .replace('\"', '') \
      .replace('.', '')

    # get the primary artist name, strip off any special chars
    artist = track['artists'][0]['name'] \
      .replace('?', '') \
      .replace('/', '') \
      .replace('\\', '') \
      .replace('\'', '') \
      .replace('\"', '') \
      .replace('.', '')

    # get the album title, strip off any special chars
    album = track['album']['name'] \
      .replace('?', '') \
      .replace('/', '') \
      .replace('\\', '') \
      .replace('\'', '') \
      .replace('\"', '') \
      .replace('.', '')

    albumTotal = track['album']['total_tracks']
    trackNum = track['track_number']

    # get the track duration as an integer 
    duration = int(track['duration_ms'])

    # get the cover art URL
    imgLoc = track['album']['images'][0]['url']

    # return values
    return id, songTitle, artist, album, duration, f'{trackNum:02}/{albumTotal:02}', imgLoc

  def _getLibraryData(self, verbose: bool = True, max=sys.maxsize):
    '''
    Retrieve all of a user's liked songs from the spotify api

    PARAMETERS:
      verbose - whether or not to log progress
      max - max songs to gather (for testing)
    '''
  
    startTime = dt.now()
  
    limit = 20  # how many tracks to return per api call
    offset = 0  # how many tracks to offset api call by
  
    # if the max songs is less than 20, set the limit to the max value
    #   so we don't pull too many values
    if max < 20:
      limit = max
  
    # get the user's tracks from the spotify api
    tracks = self.sp.current_user_saved_tracks(limit, offset)
  
    # find the total number of songs that will be retrieved (if max is assigned, the
    #   method will stop before we pull this many songs)
    total = tracks['total']

    # get data from file
    libDataFileLoc = os.path.join(self._options.outputDir, ".data", "songs.txt")
    songsFromFile = self._deserializeSongsFile(libDataFileLoc)

    for song in songsFromFile:
      if not song.id in self.songs:
        self.songs[song.id] = song
      if song.fileLoc == "":
        self.songsToDownload.append(song)
        
    if len(songsFromFile) == len(self.songs):
      if verbose: printProgress("Reading Spotify Library", total, total, startTime)
      return

    # loop until the offset value is greater than the total or max number of songs to retrieve
    while offset < total and offset < max:
      # add the limit value to the offset so our next call will pull the next page of songs
      offset += limit
    
      # log our progress
      if verbose: verbose = printProgress("Collecting Songs", offset, total, startTime)
    
      # loop through songs retrieved from the request
      for item in tracks['items']:
        # assign the track to a var
        track = item['track']
      
        id, songTitle, artist, album, duration, trackNumber, imgLoc = self._getTrackData(track)
        
        if ( id == None ):
          continue
        
        song = Song(id, songTitle, artist, album, duration, trackNumber, imgLoc)
        expectedSongLoc = song.getSaveLoc(self._options.outputDir) + '.mp3'
        
        # make sure we don't have this song already
        if not id in self.songs:
          # add this song to the songs dict, indexed by its spotify id
          self.songs[id] = song
          
          if os.path.exists(expectedSongLoc):
            song.fileLoc = expectedSongLoc
          else:
            self.songsToDownload.append(song)
    
      # send the next request
      tracks = self.sp.current_user_saved_tracks(limit, offset)
  
    # save songs datafile
    self._serializeSongsFile(libDataFileLoc)
  
    # log our progress
    if verbose: printProgress("Reading Spotify Library", offset, total, startTime)

  def _getPlaylistData(self, verbose: bool = True, max=-1):
    startTime = dt.now()
    
    playlistsDir = os.path.join( self._options.outputDir, "playlists")
    playlistsDirExists, playlistsDir = self._ensureDirectoryExists(playlistsDir, self._options.outputDir)
    
    existingPlaylists = os.listdir(playlistsDir)
  
    # get listing of playlists and add their IDs as keys to the self.playlists dict
    limit = 50
    offset = 0
    i = 0
  
    while True:
    
      pl = self.sp.current_user_playlists(limit, offset)
      playlistCount = pl['total']
    
      for i, playlist in enumerate(pl['items']):
        i += 1
        if max != -1 and i > max:
          break
      
        if verbose: verbose = printProgress("Collecting playlists", i + offset, playlistCount, startTime)
        
        # if this playlist has been saved in the last day, ignore it
        playlistFile = os.path.join(playlistsDir, playlist['name'] + '.m3u')
        if os.path.exists(playlistFile):
          timestamp = os.path.getmtime(playlistFile)
          datestamp = dt.fromtimestamp(timestamp)
          if (datestamp - dt.now()).days < 1:
            continue
        
        pi = self.sp.playlist(playlist['id'])
      
        if pi['name'] in self._options.excludePlaylists:
          continue
        
        if self._options.onlyMyPlaylists and pi['owner']['display_name'] != self._spCurrentUser:
          continue

        playlistObj = Playlist(pi['name'])
        
        for t in pi['tracks']['items']:
          if (not 'track' in t) or (t['track'] == None):
            continue
          track = t['track']
          if not track['id'] in self.songs:
            id, songTitle, artist, album, duration, trackNumber, imgLoc = self._getTrackData(track)

            if (id == None):
              continue
            
            song = Song(id, songTitle, artist, album, duration, trackNumber, imgLoc)
            self.songs[id] = song
            
            songFileLoc = song.getSaveLoc(self._options.outputDir + ".mp3")
            if not os.path.exists(songFileLoc):
              self.songsToDownload.append(song)
            else:
              song.fileLoc = songFileLoc
            
            playlistObj.songs.append(id)
        
        self.playlists[playlistObj.name] = playlistObj
    
      offset += limit
      if offset > playlistCount + limit or i > max >= 0: break
  
    if verbose: verbose = printProgress("Collecting playlists", i + offset, playlistCount, startTime)
  #endregion
  
  #region youtube download
  def _findYoutubeVideo(self, songTitle, artist, spDuration):
    '''
    Search youtube for the song and find the result with the closest duration to the spotify track 

    PARAMETERS: 
      songTitle - title of the song
      artist - song artist
      spDuration - song duration specified by spotify, in milliseconds
    RETURNS: 
      string - a youtube link to the song 
    '''

    # search youtube for the song
    s = yts.Search(F'{artist} {songTitle}')
    # try:
    # except Exception as e:
    #   return None

    # instantiate vars for the closest match
    closestMatch = ''
    closestDuration = sys.maxsize # instantiate this to the max size into so it fails later comparison 

    # loop through the results 
    for ytItem in s.resultComponents:
      # if there is no duration specified, ignore this item 
      if (not 'duration' in ytItem) or (ytItem['duration'] == None) :
        continue 

      # yt duration is formatted as MM:SS so we need to convert it to ms
      # split the duration string on ":"
      durationParts = ytItem['duration'].split(":")
      
      # check to make sure the duration string was split into 1 or 2 parts
      #   and assign them to minutes and seconds variables
      if len(durationParts) == 2:
        mins = int(durationParts[0])
        secs = int(durationParts[1])
      elif len(durationParts) == 1:
        mins = 0
        secs = int(durationParts[0])
      else:
        # if it was more than 2 or 0 parts, ignore this object
        continue

      # calculate the duration in ms 
      ytDuration = (mins * 60 + secs) * 1000

      # check that the duration is not more or less than 5 seconds from what's expected
      if abs(ytDuration - spDuration) > 5000:
        continue

      # find the absolute difference between this video's duration and the spotify 
      #   track's duration and check if it is less than the current closest match 
      if abs(ytDuration - spDuration) < abs(closestDuration - spDuration):
        # if check succeeds, assign the duration and url to variables
        closestDuration = ytDuration
        closestMatch = ytItem['link']
    
    if closestMatch == '' and artist != '':
      result = self._findYoutubeVideo(songTitle, '', spDuration)
      return result if result != '' else None
    
    # once we've checked each option, return the closest match 
    return closestMatch

  def _downloadFromYoutube(self, fileName, ytLink ):
    saveLoc = os.path.abspath( fileName )

    ydl_opts = {
      'format': 'bestaudio/best',
      # 'outtmpl': self.songsDir + '/%(title)s',  # name the file the ID of the video
      'outtmpl': saveLoc,
      'embedthumbnail': True,
      'quiet': True, 
      'noprogress': True,
      'logger': loggerOutputs,
      'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
      }, {
        'key': 'FFmpegMetadata',
      }]
    }

    try:
      with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(ytLink, download=True)
    except:
      return ""
    # extract the name of the downloaded file from the info_dict
    fileLoc = ydl.prepare_filename(info_dict)

    return fileLoc
  #endregion
  
  #region save playlists
  def _saveAllPlaylists(self, verbose:bool=True):
    startTime = dt.now()
    playlistsDir = os.path.join( self._options.outputDir, "playlists")

    playlistsDirExists, playlistsDir = self._ensureDirectoryExists(playlistsDir, self._options.outputDir)

    for i, id in enumerate(self.playlists):
      if verbose: verbose = printProgress("Saving playlists", i+1, len(self.playlists), startTime)
      pl = self.playlists[id]
      self._savePlaylistToFile(pl, playlistsDir)
    if verbose: verbose = printProgress("Saving playlists", len(self.playlists), len(self.playlists), startTime)

  def _savePlaylistToFile(self, playlistObject, outputDir ):
    fileStr = ""
    
    for trackid in playlistObject.songs:
      song = self.songs[trackid]
      fileStr += song.getM3uLine()
    
    with open( os.path.join( outputDir, playlistObject.getFileName()), 'w', encoding="utf-8" ) as f:
      f.write( fileStr )
  #endregion
  
  #region file management
  def _setFileMeta(self, fileLoc, title, artist, album, trackNum, coverUrl):
    '''
    Set the ID3 and APIC data for an mp3 file to the values pulled from spotify

    PARAMETERS:
      fileLoc - the mp3 file to be modified
      title - song title
      artist - song artist
      album - album title
      coverUrl - link to the album cover (retrieved from spotify)
    '''
  
    track, totalTracks = trackNum.split('/')
  
    # set the ID3 data using mutigen
    c = EasyID3(fileLoc + '.mp3')
    c.clear()  # clear all current tags before assigning new ones
    c['title'] = title
    c['artist'] = artist
    c['album'] = album
    c['albumartist'] = artist
    c['TRCK']: track
    c.save()
  
    # send a get request to retrieve the cover art
    cover_data = requests.get(coverUrl).content
  
    # embed the cover art in the file
    c = ID3(fileLoc + '.mp3')
    c['APIC'] = APIC(
      encoding=3,
      mime='image/jpeg',
      type=3, desc=u'Cover',
      data=cover_data
    )
    c['TRCK'] = TRCK(encoding=3, text=track)
  
    c.save()

  def _ensureDirectoryExists(self, dir, baseDir = ""):
    # remove the filename from the dir if it has one
    absDir = os.path.abspath(dir)
    outputDirAbs =  os.path.abspath(self._options.outputDir)

    # before we do all this other work, just check if the path exists and return True if it does
    if os.path.exists(dir):
      return True, dir

    # if the base dir is not set, try to set it either to the output dir defined in the options,
    #   or by getting the absolute path and replacing anything not in the dir var
    if baseDir == "":
      # if the dir is a child of the class's output dir
      if dir.startswith(outputDirAbs):
        # set the base dir to the output dir
        baseDir = outputDirAbs
        dir = absDir[len(outputDirAbs):]
      else:
        # get the absolute path from the dir var, then take everything in front of it
        baseDir = absDir[:absDir.find(dir)]

    # if the base dir can't be found, return false
    if not os.path.exists(baseDir):
      return False, ""

    dirParts = dir.replace(baseDir, "").split( os.sep )
    checkDir = baseDir

    try:
      for oneFolder in dirParts:
        oneFolder = oneFolder.replace(':', '')

        checkDir = os.path.join(checkDir, oneFolder)

        if os.path.exists(checkDir):
          continue

        os.mkdir(checkDir)
    except:
      return False, ""
    return True, checkDir

  def _serializeSongsFile( self, dataFile, songs=None ):
    if songs == None:
      songs = self.songs
  
    fileText = ""
  
    for s in songs.values():
      fileText += s.toText()
  
    with open( dataFile, mode='w', encoding="utf-8" ) as f:
      f.write( fileText )

  def _deserializeSongsFile( self, dataFile, checkForMp3=True ):
    if not os.path.exists( dataFile ):
      return []
  
    songsList = []
  
    with open( dataFile, mode='r', encoding="utf-8" ) as f:
      for l in f.readlines():
        s = Song.fromText( l )
      
        if checkForMp3 and s.fileLoc == "":
          expectedFileLoc = s.getSaveLoc( self._options.outputDir ) + '.mp3'
          if os.path.exists( expectedFileLoc ):
            s.fileLoc = expectedFileLoc
      
        songsList.append( s )
  
    return songsList
  
  def _saveFailedSongs( self ):
    fileLoc = os.path.join(self._options.outputDir, '.data', 'failedToCollect.txt' )
    fileTxt = ''
    
    for s in self.songsToDownload:
      fileTxt += f'{s.artist} - {s.songTitle} ({s.error})\n'
      
    with open(fileLoc, 'w', encoding="utf-8") as f:
      f.write(fileTxt)
  #endregion

class DownloaderOptions:
  excludePlaylists = []
  outputDir = "output/downloader/"
  onlyMyPlaylists = False

  def __init__(self, dataFile=""):
    if dataFile == "" or not os.path.exists(dataFile):
      return

    with open(dataFile, 'r') as f:
      for l in f.readlines():
        splitIndex = l.find( "=" )
        key = l[:splitIndex].strip(" \n")
        val = l[splitIndex+1:].strip(" \n")

        if key == "outputDir":
          self.outputDir = str(val).strip('\"\' ')
        if key == "onlyMyPlaylists":
          self.onlyMyPlaylists = val.upper().strip('\"\' ') == "TRUE"
        if key == "excludePlaylists":
          self.excludePlaylists = self.parseList(val)
  def parseList(self, valStr):
    valsList = []
    val = ""
    i = 0
    quote = False
    
    while i < len(valStr):
      char = valStr[i]
      
      if char == '\"' or char == '\'':
        quote = not quote
        continue
      
      if char == ',' and not quote:
        valsList.append(val.strip(' '))
        val = ""
        i += 1
        continue
      
      if char == '\\':
        i += 1
        char = valStr[i]
      
      val += char
      i += 1
    
    return valsList

class loggerOutputs:
    def error(msg):
        #print("Captured Error: "+msg)
        pass
    def warning(msg):
        # print("Captured Warning: "+msg)
        pass
    def debug(msg):
        # print("Captured Log: "+msg)
        pass

class Song:
  id = ""
  songTitle = ""
  artist = ""
  album = ""
  duration = -1
  imgLoc = ""
  fileLoc = ""
  error = ""

  def __init__(self, id, songTitle, artist, album, duration, trackNum, imgLoc, fileLoc = ""):
    self.id = id
    self.songTitle = songTitle.replace("|", '')
    self.artist = artist.replace("|", '')
    self.album = album.replace("|", '')
    self.duration = duration
    self.trackNum = trackNum
    self.imgLoc = imgLoc
    self.fileLoc = fileLoc

  @staticmethod
  def fromText(line):
    line = line.strip('\n')
    lineParts = line.split('|')

    if len(lineParts) != 8:
      return None

    id = lineParts[0]
    songTitle = lineParts[1]
    artist = lineParts[2]
    album = lineParts[3]
    duration = int(lineParts[4])
    trackNum = lineParts[5]
    imgLoc = lineParts[6]
    fileLoc = lineParts[7]

    return Song( id, songTitle, artist, album, duration, trackNum, imgLoc, fileLoc )

  def toText(self):
    return f"{self.id}|{self.songTitle}|{self.artist}|{self.album}|{self.duration}|{self.trackNum}|{self.imgLoc}|{self.fileLoc}\n"

  def getM3uLine(self):
    return f'{self.artist}/{self.album}/{self.fileLoc}\n'
  
  def getSaveLoc(self, baseDir):
    artist = self.artist.replace(':', '')
    album = self.album.replace(':', '')
    title = self.songTitle.replace(';', '')
    
    return os.path.join(baseDir, "tracks", artist, album, title)
  
class Playlist:
  name = ""
  songs = []
  
  def __init__(self, name):
    self.name = name \
      .replace( '\\', ' ' ) \
      .replace( '/', ' ' ) \
      .replace( '?', ' ' )
  
  def getFileName( self ):
    return self.name\
      .replace( "<", "" ) \
      .replace( ">", "" ) \
      .replace( "\\", "" ) \
      .replace( "/", "" ) \
      + ".m3u"