# Algorand Smart Contract development hands-on class

## Environment setup
How to properly create the develpment environment:
* Connect to the network through:
  * [Sandbox](https://github.com/algorand/sandbox)
  * [Purestake](https://developer.purestake.io/) 


* Setup environment:
  * `pip3 install virtualenv`
  * `virtualenv venv`
  * `source venv/bin/activate`
  * `pip3 install pyteal py-algorand-sdk`
  
* Test our environment with: https://developer.algorand.org/docs/sdks/python/

## First Contract

In this tutorial we are seeing how to create a simple Counter smart contract that update the value of a variable on a smart contract.

Following this tutorial:  https://developer.algorand.org/docs/get-details/dapps/pyteal/

## Auction with plain bidding

In this tutorial, we see a more complex example of a smart contract handling an auction for the sale of an NFT.

The smart contract stores in the global storage only the highest bid and the bidder that made it. 
When the auction terminates, the seller or the creator of the auction delete the application and transfer the NFT to the winner
and the winning bid amount to the seller.

## Auction with commitment

In this tutorial, we increase the level of complexity of our auction. 
We store, at first, in the local state a commitment of the bidders of each bidder along with a token deposit to ensure good behaviour. 
Then, in a second phase, each bidder reveal its bid and only the highest bid and bidder it's stored in the global state. 
Each bidder will receive its token deposit back.
The auction terminates as before.

## Beaker Tutorial

In this tutorial, we have a look at how to use the Beaker framework.
Following this tutorial: https://algorand-devrel.github.io/beaker/html/usage.html#state-management.