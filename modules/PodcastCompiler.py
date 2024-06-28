import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from datetime import datetime


# PodcastCompiler
# A tool used to compile all episodes from numerous podcasts into a single playlist
class SpotifyPlaylistCompiler:
  options = None
  redirectUri = "http://localhost:8080"
  scope = "playlist-modify-private user-library-read user-read-playback-position"
  
  def __init__(self, options):
    # assign parameters to isntance variables
    self.options = options
    
    # open the input file
    f = open(options.compilerData).readlines()
    
    self.startDate = datetime.strptime(f[0].strip(), '%Y-%m-%d') # date to start collecting podcasts from (last date this program was run)
    self.playlistId = f[1] # Spotify ID for the playlist that episodes will be added to
    self.podcastIds = [] # Spotify IDs for podcasts that will be added to the playlist
    
    # iterate through lines in the file, starting at line 3
    for line in f[2:]:
      self.podcastIds.append(line.strip()) # add each subsequent line (Podcast URIs) to a list
      
    # get authenticated spotify client
    self.sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=self.options.spotifyClientId, client_secret=self.options.spotifyClientSecret,
                                                        redirect_uri=self.redirectUri, scope=self.scope))
    
    # instantiate a list of the episode URIs and dates in the current playlist
    self.playlistCurrent_ids = []
    self.playlist_dates = []
    self.toRemove_uris = []
    
  
  def runCompileProcess(self):
    self.getPlaylistItems()
    self.removePodcastsFromPlaylist()
    self.addAllPodcastsToPlaylist()
    self.updateDataFile()
  
  def getPlaylistItems(self):
    limit = 100
    offset = 0
    
    while True:
      # get al the current items in the playlist
      playlistCurrent = self.sp.playlist_items(self.playlistId, limit=limit, offset=offset)
      
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
        
        if e['resume_point']['fully_played'] or e['resume_point']['resume_position_ms'] > duration * .95:
          self.toRemove_uris.append(uri)
  
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
      self.sp.playlist_add_items(self.playlistId, [uri], index)
      # add the episode to the list of existing episodes
      self.playlist_dates.insert(index, (epId, releaseDate))
  
  def addAllPodcastsToPlaylist(self):
    # iterate through podcasts loaded during instantiation
    for podId in self.podcastIds:
      # add all episodes of that podcast to the playlist
      self.addOnePodcastToPlaylist(podId)
  
  def removePodcastsFromPlaylist(self):
    chunks = [self.toRemove_uris[i:i+50] for i in range(0, len(self.toRemove_uris), 50)]
    
    for chunk in chunks:
      r = self.sp.playlist_remove_all_occurrences_of_items(self.playlistId, chunk)
      pass
  
  def updateDataFile(self):
    # define a tmp file location
    tmpFile = self.options.compilerData + '.tmp'
    
    # open the datafile and assign it to a line array
    f = open(self.options.compilerData, 'r+')
    lines = f.readlines()
    
    # change the first line to today's date
    lines[0] = datetime.now().strftime('%Y-%m-%d') + "\n"
  
    # create the tmp file and write to it
    tmp = open(tmpFile, 'w')
    tmp.write(''.join(lines))
  
    # close both files
    tmp.close()
    f.close()
  
    # delete the original datafile
    os.remove(self.options.compilerData)
    # rename the tmp file as the datafile
    os.rename(tmpFile, self.options.compilerData)
  
  
def main():
  # instantiate the compiler class
  pc = SpotifyPlaylistCompiler("compilerData.txt")
  pc.addAllPodcastsToPlaylist()
  pc.updateDataFile()
  

if __name__ == "__main__":
  main()
