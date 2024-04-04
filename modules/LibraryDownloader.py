from msilib.schema import Verb
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
from mutagen.id3 import ID3, APIC

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

  def downloadFullLibrary(self, verbose:bool=True):
    '''
    Download all songs in your spotify library and compile .txt files contating playlist data
    '''

    # get user's "liked songs" via the spotify api
    self._getLibraryData(verbose)

    # get user's playlist information via the spotify api
    self._getPlaylistData(verbose)

    # save playlists to .txt files
    self._saveAllPlaylists(verbose)

    # search youtube for songs and download them as mp3
    self._downloadAllSongs(verbose)
  
  def _downloadAllSongs(self, verbose:bool=True):
    '''
    iterate through self.songs, search youtube for each song and download it as an .mp3
    '''

    # create a listing of songs that have already been downloaded 
    #   so we don't waste time downloading the same songs twice
    alreadyDownloaded = [f.replace(".mp3", "") for f in os.listdir( self._options.outputDir )]

    # loop through songs collected from spotify 
    for i, id in enumerate(self.songs):
      # print to console 
      if verbose: printProgress("Downloading Songs", i, len(self.songs))

      # get the track object
      track = self.songs[id]

      # download the song and save it to the output directory
      self._downloadOneSong( track, alreadyDownloaded )

  def _downloadOneSong(self, track, alreadyDownloaded):
    '''
    search youtube for a song and download the audio

    PARAMETERS:
      track - the spotify object for the song
      alreadyDownloaded - a list of "<artist> - <song title>" containing the songs which have already been downloaded
    '''
    
    # get relevant data from the track object
    songTitle, artist, album, duration, imgLoc = self._getTrackData(track)
    
    # set the file name to <artist> - <title> but don't append the '.mp3' yet
    fileName = f'{artist} - {songTitle}'

    # check if this song has already been downloaded 
    if fileName in alreadyDownloaded:
      # return if it has 
      return

    # get find the correct youtube video and find a link 
    ytLink = self._findYoutubeVideo(songTitle, artist, duration)

    # download the file and assign a variable to the new location 
    fileLoc = self._downloadFromYoutube(fileName, ytLink)

    # set ID3/APIC metadata for the file 
    self._setFileMeta(fileLoc, songTitle, artist, album, imgLoc)
      
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

    # get the track duration as an integer 
    duration = int(track['duration_ms'])

    # get the cover art URL
    imgLoc = track['album']['images'][0]['url']

    # return values
    return songTitle, artist, album, duration, imgLoc

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
      if len(durationParts) == 1:
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

  def _downloadFromYoutube(self, fileName, ytLink):
    saveLoc = os.path.join(self._options.outputDir, f'{fileName}' )
    saveLoc = os.path.abspath( saveLoc )

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

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
      info_dict = ydl.extract_info([ytLink][0], download=True)
      
    # extract the name of the downloaded file from the info_dict
    fileLoc = ydl.prepare_filename(info_dict)

    return fileLoc

  def _setFileMeta(self, fileLoc, title, artist, album, coverUrl):
    '''
    Set the ID3 and APIC data for an mp3 file to the values pulled from spotify

    PARAMETERS: 
      fileLoc - the mp3 file to be modified
      title - song title
      artist - song artist
      album - album title
      coverUrl - link to the album cover (retrieved from spotify)
    '''

    # set the ID3 data using mutigen
    c = EasyID3(fileLoc + '.mp3')
    c.clear() # clear all current tags before assigning new ones
    c['title'] = title
    c['artist'] = artist
    c['album'] = album
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

    c.save()

  def _getLibraryData(self, verbose:bool=True, max = sys.maxsize):
    '''
    Retrieve all of a user's liked songs from the spotify api

    PARAMETERS: 
      verbose - whether or not to log progress
      max - max songs to gather (for testing)
    '''

    limit = 20 # how many tracks to return per api call
    offset = 0 # how many tracks to offset api call by

    # if the max songs is less than 20, set the limit to the max value 
    #   so we don't pull too many values
    if max < 20:
      limit = max
      
    # get the user's tracks from the spotify api 
    tracks = self.sp.current_user_saved_tracks(limit, offset)
    
    # find the total number of songs that will be retrieved (if max is assigned, the 
    #   method will stop before we pull this many songs)
    total = tracks['total']

    # loop until the offset value is greater than the total or max number of songs to retrieve
    while offset < total and offset < max:
      # add the limit value to the offset so our next call will pull the next page of songs
      offset += limit
      
      # log our progress
      if verbose: printProgress("Collecting Songs", offset, total)
      
      # loop through songs retrieved from the request
      for item in tracks['items']:
        # assign the track to a var 
        track = item['track']
        
        # make sure we don't have this song already 
        if not track['id'] in self.songs:
          # add this song to the songs dict, indexed by its spotify id
          self.songs[track['id']] = track

      # send the next request 
      tracks = self.sp.current_user_saved_tracks(limit, offset)

    # log our progress
    if verbose: printProgress("Collecting Songs", offset, total)
    
  def _getPlaylistData(self, verbose:bool=True, max=-1):
    # get listing of playlists and add their IDs as keys to the self.playlists dict
    limit = 50
    offset = 0
    i = 0

    while True:

      pl = self.sp.current_user_playlists(limit, offset)
      playlistCount = pl['total']

      for i, playlist in enumerate(pl['items']):
        i+=1
        if max != -1 and i > max:
          break


        if verbose: printProgress("Collecting playlists", i + offset, playlistCount)
        pi = self.sp.playlist(playlist['id'])

        if pi['name'] in self._options.excludePlaylists:
          continue

        if self._options.onlyMyPlaylists and pi['owner']['display_name'] != self._spCurrentUser:
          continue

        self.playlists[playlist['id']] = pi

        for t in pi['tracks']['items']:
          if (not 'track' in t) or (t['track'] == None):
            continue
          track = t['track']
          if not track['id'] in self.songs:
            self.songs[track['id']] = track 


      offset += limit
      if offset > playlistCount or i > max: break
   
  def _saveAllPlaylists(self, verbose:bool=True):
    outDir = os.path.join( self._options.outputDir, "playlists")

    if not os.path.exists( outDir ):
      os.mkdir( outDir )

    for i, id in enumerate(self.playlists):
      if verbose: printProgress("Saving playlists", i+1, len(self.playlists))
      pl = self.playlists[id]
      self._savePlaylistToFile(pl, outDir)

  def _savePlaylistToFile(self, playlistObject, outputDir ):
    playlistName = playlistObject['name']
    
    fileStr = "Name\tArtist\tComposer\tAlbum\tGrouping\tWork\tMovement Number\tMovement Count\tMovement Name\tGenre" \
              "\tSize\tTime\tDisc Number\tDisc Count\tTrack Number\tTrack Count\tYear\tDate Modified\tDate Added\t" \
              "Bit Rate\tSample Rate\tVolume Adjustment\tKind\tEqualizer\tComments\tPlays\tLast Played\tSkips\t" \
              "Last Skipped\tMy Rating\tLocation\n"
    
    for t in playlistObject['tracks']['items']:
      trackObject = t['track']
      
      if ( trackObject is None or trackObject['type'] != 'track' ):
        continue
      
      fileStr += trackObject['name'] + '\t' # name
      fileStr += ','.join([a['name'] for a in trackObject['artists']]) + '\t' # artist
      fileStr += '\t' # composer
      fileStr += trackObject['album']['name'] + '\t' # album
      fileStr += '\t' # grouping
      fileStr += '\t' # work
      fileStr += '\t' # movement number
      fileStr += '\t' # movement count
      fileStr += '\t' # movement name
      fileStr += '\t' # genre
      fileStr += '\t' # size
      fileStr += '\t' # time
      fileStr += '\n'
    
    if ( len(fileStr.split('\n')) == 2 ):
      return
    
    playlistName = playlistName \
      .replace( '\\', ' ' ) \
      .replace( '/', ' ' ) \
      .replace( '?', ' ' )
    
    with open( os.path.join( outputDir, playlistName + ".txt"), 'w', encoding="utf-8" ) as f:
      f.write( fileStr )


class DownloaderOptions:
  excludePlaylists = []
  outputDir = "output/downloader/"
  onlyMyPlaylists = False

  def __init__(self, dataFile=""):
    if dataFile == "":
      return

    with open(dataFile, 'r') as f:
      for l in f.readlines():
        splitIndex = l.find( "=" )
        key = l[:splitIndex].strip("\n")
        val = l[splitIndex+1:].strip("\n")

        if key == "excludePlaylists":
          self.excludePlaylists = [x.strip('\'') for x in val.split(',')]
        if key == "outputDir":
          self.outputDir = str(val)
        if key == "onlyMyPlaylists":
          self.onlyMyPlaylists = val.upper() == "TRUE"


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
