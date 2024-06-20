import argparse
from modules.PodcastCompiler import SpotifyPlaylistCompiler
from modules.LibraryDownloader import Downloader
from util.UtilOptions import UtilOptions

def runDownloader( options ):
  dl = Downloader(options)
  dl.downloadFullLibrary( True )

def runCompiler(options ):
  # instantiate the class
  pc = SpotifyPlaylistCompiler(options.compilerData, options.spotifyClientId, options.spotifyClientSecret)

  # add podcasts to playlist
  pc.addAllPodcastsToPlaylist()
  
  # update and save the datafile
  pc.updateDataFile()

def runMkvConvert(options):
  pass

def parseArgs():
  parser = argparse.ArgumentParser(description='Optional app description')
  
  parser.add_argument( 'process', nargs='?', type=int, help='the process to run')
  parser.add_argument( '--options', type=str, help='the options.txt file' )

  return parser.parse_args()

def main(*args):
  optionsFile = "./dataFiles/options.txt"
  
  args = parseArgs()
  
  if args.options != None:
    optionsFile = args.options
  
  options = UtilOptions(optionsFile)
  
  process = args.process
  
  if process == None:
    print("Which module would you like to use?")
    print("1: Spotify Downloader (Offline your entire spotify library)")
    print("2: Podcast Compiler (Add all your podcasts to one playlist)")
    print("3: MKV Converter (Convert MKV files to MP4)")
    
    process = input()
  
    while not process.isdecimal():
      process = input("Please enter a number:")
      
    process = int( process )
  
  match process:
    case 1:
      runDownloader(options)
    case 2:
      runCompiler(options)
    case 3:
      runMkvConvert(options)
    case -1:
      runDownloader(options)
      runCompiler(options)

main()