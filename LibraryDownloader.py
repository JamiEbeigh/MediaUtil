import spotipy
from spotipy.oauth2 import SpotifyOAuth


class Downloader:
  _ClientId = ""
  _ClientSecret = ""
  _OutputDir = ""
  _RedirectUri = "http://localhost:8080"
  _Scope = "user-library-read"
  
  playlists = []
  songs = []
  
  def __init__(self, clientId, clientSecret, outputDir ):
    self._ClientId = clientId
    self._ClientSecret = clientSecret
    self._OutputDir = outputDir
    
    # get authenticated spotify client
    self.sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=self._ClientId, client_secret=self._ClientSecret,
                                                        redirect_uri=self._RedirectUri, scope=self._Scope))

  def downloadFullLibrary(self):
    self._getLibraryData()
  
  def makePlaylistFiles(self):
    pass
  
  def _getSongsInLibrary(self):
    pass
  
  def _downloadOneSong(self):
    pass
  
  def _getLibraryData(self):
    limit = 20 # how many tracks to return per api call
    offset = 0 # how many tracks to offset api call by
    
    while True:
      tracks = self.sp.current_user_saved_tracks(limit, offset)
      
      