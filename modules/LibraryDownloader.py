import os
import sys
import requests
from util import CredentialsManager
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from util.outputManager import printProgress
import youtubesearchpython as yts
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

  playlists = {}
  songs = {}
  
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

  def downloadFullLibrary(self, verbose:bool=True, collectPlaylists:bool=False):
    '''
    Download all songs in your spotify library and compile .txt files contating playlist data
    '''

    # get user's "liked songs" via the spotify api
    self._getLibraryData(verbose)

    if collectPlaylists:
      # get user's playlist information via the spotify api
      self._getPlaylistData(verbose)

      # save playlists to .txt files
      self._saveAllPlaylists(verbose)

    # search youtube for songs and download them as mp3
    self._downloadAllSongs(verbose)
  
  #region downloadSongs
  def _downloadAllSongs(self, verbose:bool=True):
    '''
    iterate through self.songs, search youtube for each song and download it as an .mp3
    '''

    startTime = dt.now()

    if not os.path.exists(os.path.join(self._options.outputDir, "tracks")):
      os.mkdir(os.path.join(self._options.outputDir, "tracks"))

    collected = 0
    total = len( self.songs )

    # loop through songs collected from spotify 
    for i, id in enumerate(self.songs):
      # print to console 
      if verbose: verbose = printProgress("Downloading Songs", collected, total, startTime)

      # get the track object
      track = self.songs[id]

      # download the song and save it to the output directory
      downloadResult = self._downloadOneSong( track )

      if downloadResult == None:
        total -= 1
      elif downloadResult:
        collected += 1
      
      # if collected % 50 == 0:
      #   self._saveAllPlaylists()

  def _downloadOneSong(self, track ):
    '''
    search youtube for a song and download the audio

    PARAMETERS:
      track - the spotify object for the song
      alreadyDownloaded - a list of "<artist> - <song title>" containing the songs which have already been downloaded
    '''

    # set the file name to <artist> - <title> but don't append the '.mp3' yet
    fileName = os.path.join( self._options.outputDir, "tracks", track.artist, track.album, track.songTitle )

    if not os.path.exists( os.path.join( self._options.outputDir, "tracks", track.artist ) ):
      os.mkdir(os.path.join(self._options.outputDir, "tracks", track.artist ) )

    if not os.path.exists( os.path.join( self._options.outputDir, "tracks", track.artist, track.album ) ):
      os.mkdir(os.path.join( self._options.outputDir, "tracks", track.artist, track.album ))

    # check if this song has already been downloaded 
    if os.path.exists(fileName + ".mp3"):
      track.fileLoc = os.path.abspath(fileName + '.mp3')
      # return if it has 
      return None

    # get find the correct youtube video and find a link 
    ytLink = self._findYoutubeVideo(track.songTitle, track.artist, track.duration)

    if ytLink == None:
      return False

    # download the file and assign a variable to the new location 
    fileLoc = self._downloadFromYoutube(fileName, ytLink)

    if ( fileLoc == "" ):
      return False
    
    track.fileLoc = os.path.abspath(fileLoc)

    # set ID3/APIC metadata for the file 
    self._setFileMeta(fileLoc, track.songTitle, track.artist, track.album, track.trackNum, track.imgLoc)

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
  
    # get data from file
    libDataFileLoc = os.path.join(self._options.outputDir, ".data", "songs")
    if os.path.exists(libDataFileLoc):
      with open(libDataFileLoc, 'r', encoding="utf-8") as f:
        for l in f.readlines():
          s = Song.fromText(l)
        
          self.songs[s.id] = s
  
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
  
    if total == len(self.songs.keys()):
      if verbose: verbose = printProgress("Collecting Songs", total, total, startTime)
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
      
        # make sure we don't have this song already
        if not id in self.songs:
          # add this song to the songs dict, indexed by its spotify id
          self.songs[id] = song
    
      # send the next request
      tracks = self.sp.current_user_saved_tracks(limit, offset)
  
    # save songs datafile
    songsTxt = ""
  
    for s in self.songs.values():
      songsTxt += s.toText()
  
    dataFolder = os.path.join(self._options.outputDir, ".data")
    if not os.path.exists(dataFolder):
      os.mkdir(dataFolder)
  
    with open(libDataFileLoc, mode='w', encoding="utf-8") as f:
      f.write(songsTxt)
  
    # log our progress
    if verbose: verbose = printProgress("Collecting Songs", offset, total, startTime)

  def _getPlaylistData(self, verbose: bool = True, max=-1):
    startTime = dt.now()
    
    playlistsDir = os.path.join( self._options.outputDir, "playlists")
    if not os.path.exists(playlistsDir):
      os.mkdir(playlistsDir)
    
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
    try:
      s = yts.Search(F'{artist} {songTitle}')
    except:
      return None

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

      # find the absolute difference between this video's duration and the spotify 
      #   track's duration and check if it is less than the current closest match 
      if abs(ytDuration - spDuration) < abs(closestDuration - spDuration):
        # if check succeeds, assign the duration and url to variables
        closestDuration = ytDuration
        closestMatch = ytItem['link']
    
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
    outDir = os.path.join( self._options.outputDir, "playlists")

    if not os.path.exists( outDir ):
      os.mkdir( outDir )

    for i, id in enumerate(self.playlists):
      if verbose: verbose = printProgress("Saving playlists", i+1, len(self.playlists), startTime)
      pl = self.playlists[id]
      self._savePlaylistToFile(pl, outDir)
    if verbose: verbose = printProgress("Saving playlists", len(self.playlists), len(self.playlists), startTime)

  def _savePlaylistToFile(self, playlistObject, outputDir ):
    fileStr = ""
    
    for trackid in playlistObject.songs:
      song = self.songs[trackid]
      fileStr += song.getM3uLine()
    
    with open( os.path.join( outputDir, playlistObject.name + ".m3u"), 'w', encoding="utf-8" ) as f:
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

  def __init__(self, id, songTitle, artist, album, duration, trackNum, imgLoc):
    self.id = id
    self.songTitle = songTitle.replace("|", '')
    self.artist = artist.replace("|", '')
    self.album = album.replace("|", '')
    self.duration = duration
    self.trackNum = trackNum
    self.imgLoc = imgLoc

  @staticmethod
  def fromText(line):
    line = line.strip('\n')
    lineParts = line.split('|')

    if len(lineParts) != 7:
      return None

    id = lineParts[0]
    songTitle = lineParts[1]
    artist = lineParts[2]
    album = lineParts[3]
    duration = int(lineParts[4])
    trackNum = lineParts[5]
    imgLoc = lineParts[6]

    return Song( id, songTitle, artist, album, duration, trackNum, imgLoc )

  def toText(self):
    return f"{self.id}|{self.songTitle}|{self.artist}|{self.album}|{self.duration}|{self.trackNum}|{self.imgLoc}\n"

  def getM3uLine(self):
    return f'{self.artist}/{self.album}/{self.fileLoc}\n'
  
class Playlist:
  name = ""
  songs = []
  
  def __init__(self, name):
    self.name = name \
      .replace( '\\', ' ' ) \
      .replace( '/', ' ' ) \
      .replace( '?', ' ' )