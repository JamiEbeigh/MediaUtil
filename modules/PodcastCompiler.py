import os
import spotipy
import uuid
from spotipy.oauth2 import SpotifyOAuth
from spotipy.oauth2 import SpotifyPKCE
from datetime import datetime
import json

from util.UtilOptions import UtilOptions


# PodcastCompiler
# A tool used to compile all episodes from numerous podcasts into a single playlist
class SpotifyPlaylistCompiler:
  options = None
  toDelete = {}
  
  def __init__(self, options):
    # assign parameters to isntance variables
    self.options = options
    
    self.parseCompilerData()
    
    # get authenticated spotify client
    self.sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=self.options.spotifyClientId, client_secret=self.options.spotifyClientSecret,
                                                        redirect_uri=self.options.redirectUri, scope=self.options.scope, open_browser=False))
    
    # instantiate a list of the episode URIs and dates in the current playlist
    self.playlistCurrent_ids = []
    self.playlist_dates = []
    self.toRemove_uris = []
    
  
  def runCompileProcess(self):
    self.getPlaylistItems()
    self.removePodcastsFromPlaylist()
    self.addAllPodcastsToPlaylist()
    self.updateDataFile()
    print("Done!")
  
  def getPlaylistItems(self):
    print( "Getting playlist info" )
    
    limit = 100
    offset = 0
    
    while True:
      # get al the current items in the playlist
      playlistCurrent = self.sp.playlist_items(self.options.podcastPlaylist, limit=limit, offset=offset)
      
      offset += limit
      
      if not 'items' in playlistCurrent \
        or playlistCurrent['items'] == None \
        or len(playlistCurrent['items']) == 0:
        break
      
      # loop through tracks in the current playlist
      for i in playlistCurrent['items']:
        # make sure the object has the right data
        if "track" in i and i['track'] is not None:
          track = i["track"]  # get the track (episode) object
          id = track['id']  # get the episode URI
          
          self.playlistCurrent_ids.append(id)  # add the episode ID to the list of current IDs
        else:
          continue
    
    for i in range(0, len(self.playlistCurrent_ids), 50):
      chunk = self.playlistCurrent_ids[i:i+50]
      spEps = self.sp.episodes(chunk)
      
      for e in spEps['episodes']:
        id = e['id']
        uri = e['uri']
        releaseDate = datetime.strptime(e["release_date"], '%Y-%m-%d')
        self.playlist_dates.append((id, releaseDate))
        
        duration = e['duration_ms']
        
        played = e['resume_point']['fully_played'] or e['resume_point']['resume_position_ms'] > duration * .95
        
        if uri in self.toDelete and not played:
          del self.toDelete[uri]
        
        if played and not uri in self.toDelete:
          self.toDelete[uri] = datetime.now().strftime('%Y-%m-%d')
        
  def addOnePodcastToPlaylist(self, podcastUid):
    # get list of episodes for this podcast
    eps = self.sp.show_episodes(podcastUid)
    
    # loop through each episode
    for newEp in eps["items"]:
      # get the ID and release date
      epId = newEp["id"]
      uri = newEp['uri']
      releaseDate = datetime.strptime(newEp["release_date"], '%Y-%m-%d')
      
      # ignore the episode if it was released before the start date specified in the datafile
      if self.startDate > releaseDate:
        continue
        
      duration = newEp['duration_ms']
      
      if newEp['resume_point']['fully_played'] or newEp['resume_point']['resume_position_ms'] > duration * .95:
        continue

      
      # ignore the episode if it is already on the playlist
      if epId in self.playlistCurrent_ids:
        continue
      
      # find where to insert the new episode
      index = 0 # keep track of our index
      
      # iterate through dates collected during initialization
      for existingEp in self.playlist_dates:
        # check if the newEp is more recent
        if releaseDate > existingEp[1]:
          index += 1 # iterate the index if not
        else:
          break # break the loop if it is
      
      # add the episode to the playlist at the index that just found
      self.sp.playlist_add_items(self.options.podcastPlaylist, [uri], index)
      # add the episode to the list of existing episodes
      self.playlist_dates.insert(index, (epId, releaseDate))
  
  def addAllPodcastsToPlaylist(self):
    print( "Adding new episodes")
    # iterate through podcasts loaded during instantiation
    for podId in self.options.podcasts:
      # add all episodes of that podcast to the playlist
      self.addOnePodcastToPlaylist(podId)
  
  def removePodcastsFromPlaylist(self):
    print( "Removing old episodes")
    toRemove = []
    items = self.toDelete.items()
    for uri, dateStr in items:
      date = datetime.strptime(dateStr,'%Y-%m-%d')
      if (datetime.now() - date).days >= self.options.daysToWaitBeforeRemoving:
        toRemove.append(uri)
    
    for uri in toRemove:
      del self.toDelete[uri]
    
    chunks = [toRemove[i:i+50] for i in range(0, len(toRemove), 50)]
    
    for chunk in chunks:
      self.sp.playlist_remove_all_occurrences_of_items(self.options.podcastPlaylist, chunk)

  def parseCompilerData(self):
    if not os.path.exists(self.options.compilerData):
      self.options.compilerData = os.path.join('../', self.options.compilerData)
    
    f = open(self.options.compilerData)
  
    try:
      obj = json.load(f)
    
      self.startDate = datetime.strptime( obj['startDate'], '%Y-%m-%d' )
      self.toDelete = obj['toDelete']
    except:
      self.startDate = datetime.now()
  
  def updateDataFile(self):
    obj = {
      'startDate': datetime.now().strftime('%Y-%m-%d'),
      'toDelete': self.toDelete
    }
    
    objStr = json.dumps( obj, sort_keys=False, indent=2 )
    
    f = open( self.options.compilerData, 'w' )
    f.write(objStr)
    f.close()
    
  
def main():
  optionsFile = "./dataFiles/options.txt"
  options = UtilOptions(optionsFile)
  
  pc = SpotifyPlaylistCompiler(options)
  pc.runCompileProcess()
  

if __name__ == "__main__":
  main()
