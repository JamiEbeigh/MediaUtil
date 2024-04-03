import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from datetime import datetime


# PodcastCompiler
# A tool used to compile all episodes from numerous podcasts into a single playlist
class SpotifyPlaylistCompiler:
  clientId = ""
  clientSecret = ""
  redirectUri = "http://localhost:8080"
  scope = "playlist-modify-private user-library-read"
  dataFile = ""
  
  def __init__(self, datafile, clientId, clientSecret):
    # assign parameters to isntance variables
    self.dataFile = datafile
    self.clientId = clientId
    self.clientSecret = clientSecret
    
    # open the input file
    f = open(datafile).readlines()
    
    self.startDate = datetime.strptime(f[0].strip(), '%Y-%m-%d') # date to start collecting podcasts from (last date this program was run)
    self.playlistId = f[1] # Spotify ID for the playlist that episodes will be added to
    self.podcastIds = [] # Spotify IDs for podcasts that will be added to the playlist
    
    # iterate through lines in the file, starting at line 3
    for line in f[2:]:
      self.podcastIds.append(line.strip()) # add each subsequent line (Podcast URIs) to a list
      
    # get authenticated spotify client
    self.sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=self.clientId, client_secret=self.clientSecret,
                                                        redirect_uri=self.redirectUri, scope=self.scope))
    # get al the current items in the playlist
    playlistCurrent = self.sp.playlist_items(self.playlistId)
    
    # instantiate a list of the episode URIs and dates in the current playlist
    self.playlistCurrent_ids = []
    self.playlist_dates = []
    
    # loop through tracks in the current playlist
    for track in playlistCurrent['items']:
      # make sure the object has the right data
      if "track" in track and track['track'] is not None:
        track = track["track"] # get the track (episode) object
        uri = track['uri'] # get the episode URI
        
        ep = self.sp.episode(uri) # get the full episode data using the URI
        
        releaseDate = datetime.strptime(ep["release_date"], '%Y-%m-%d') # get the episode release date
        
        self.playlistCurrent_ids.append(uri) # add the episode ID to the list of current IDs
        self.playlist_dates.append((uri, releaseDate)) # add the uri and release date to the list of dates
      else:
        continue
  
  def addOnePodcastToPlaylist(self, podcastUid):
    # get list of episodes for this podcast
    eps = self.sp.show_episodes(podcastUid)
    
    # loop through each episode
    for newEp in eps["items"]:
      # get the ID and release date
      epId = newEp["uri"]
      releaseDate = datetime.strptime(newEp["release_date"], '%Y-%m-%d')
      
      # ignore the episode if it was released before the start date specified in the datafile
      if self.startDate > releaseDate:
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
      self.sp.playlist_add_items(self.playlistId, [epId], index)
      # add the episode to the list of existing episodes
      self.playlist_dates.insert(index, (epId, releaseDate))
  
  def addAllPodcastsToPlaylist(self):
    # iterate through podcasts loaded during instantiation
    for podId in self.podcastIds:
      # add all episodes of that podcast to the playlist
      self.addOnePodcastToPlaylist(podId)
  
  def updateDataFile(self):
    # define a tmp file location
    tmpFile = self.dataFile + '.tmp'
    
    # open the datafile and assign it to a line array
    f = open(self.dataFile, 'r+')
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
    os.remove(self.dataFile)
    # rename the tmp file as the datafile
    os.rename(tmpFile, self.dataFile)
  
  
def main():
  # instantiate the compiler class
  pc = SpotifyPlaylistCompiler("compilerData.txt")
  pc.addAllPodcastsToPlaylist()
  pc.updateDataFile()
  

if __name__ == "__main__":
  main()
