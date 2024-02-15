from util import CredentialsManager
from PodcastCompiler import SpotifyPlaylistCompiler
from LibraryDownloader import Downloader


SpotifyCredentialsFile = "./datafiles/SpotifyCredentials.txt"
CompilerDataFile = "./datafiles/compilerData.txt"

def runDownloader():
  # get the client credentials
  success, clientId, clientSecret = CredentialsManager.getSpotifyCredentials(SpotifyCredentialsFile)
  
  # check if the crednetials were retrieved successfully
  if not success:
    print("Could not load spotify credentials from", SpotifyCredentialsFile)

  print( "ID:", clientId )
  print( "SE:", clientSecret)

  dl = Downloader( clientId, clientSecret, "output/downloader/")
  dl.downloadFullLibrary()

def runCompiler():
  # get the client credentials
  success, clientId, clientSecret = CredentialsManager.getSpotifyCredentials(SpotifyCredentialsFile)
  
  # check if the crednetials were retrieved successfully
  if not success:
    print("Could not load spotify credentials from", SpotifyCredentialsFile)
    
  # instantiate the class
  pc = SpotifyPlaylistCompiler(CompilerDataFile, clientId, clientSecret)
  # add podcasts to playlist
  pc.addAllPodcastsToPlaylist()
  # update and save the datafile
  pc.updateDataFile()


def main():
  print("Which module would you like to use?")
  print("1: Spotify Downloader (Offline your entire spotify library)")
  print("2: Podcast Compiler (Add all your podcasts to one playlist)")
  
  choice = input()
  
  while not choice.isdecimal():
    choice = input("Please enter a number:")
    
  choice = int( choice )
  
  match choice:
    case 1:
      runDownloader()
    case 2:
      runCompiler()


def test():
  runDownloader()
  

main()