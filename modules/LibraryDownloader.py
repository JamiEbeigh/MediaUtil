from msilib.schema import Verb
from tkinter import OFF
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from util.outputManager import printProgress

class Downloader:
  _ClientId = ""
  _ClientSecret = ""
  _OutputDir = ""
  _RedirectUri = "http://localhost:8080"
  _Scope = "user-library-read playlist-read-private"
  
  playlists = {}
  songs = {}
  
  def __init__(self, clientId, clientSecret, outputDir ):
    self._ClientId = clientId
    self._ClientSecret = clientSecret
    self._OutputDir = outputDir
    
    # get authenticated spotify client
    self.sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=self._ClientId, client_secret=self._ClientSecret,
                                                        redirect_uri=self._RedirectUri, scope=self._Scope))

  def downloadFullLibrary(self, verbose:bool = False):

    # self._getLibraryData(verbose)
    self._getPlaylistData(verbose)
  
  def makePlaylistFiles(self):
    pass
  
  def _getSongsInLibrary(self):
    pass
  
  def _downloadOneSong(self):
    pass
  
  def _getLibraryData(self, verbose:bool=False):
    limit = 20 # how many tracks to return per api call
    offset = 0 # how many tracks to offset api call by

    total = 0;

    while True:
      tracks = self.sp.current_user_saved_tracks(limit, offset)
      total = tracks['total']

      if verbose: printProgress("Collecting Songs", offset, total)
      
      for item in tracks['items']:
        track = item['track']
        self.songs[track['id']] = track

      offset += limit

      if offset > total:
        break 

    if verbose: print()

  def _getPlaylistData(self, verbose:bool=False):
    # get listing of playlists and add their IDs as keys to the self.playlists dict
    limit = 50
    offset = 0
    
    while True:
      pl = self.sp.current_user_playlists(limit, offset)
      playlistCount = pl['total']

      for item in pl['items']:
        self.playlists[item['id']] = []

      offset += limit
      if offset > playlistCount: break


    


    owo = 'uwu'

    # loop through playlists and get all songs
    # add songs IDs to playlist dict