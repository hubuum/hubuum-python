# What is hubuum?

Hubuum is a REST service that provides a shared interface for your resources.

## Why hubuum?

Most content management systems (CMDBs) are strongly opinionated. They provide fairly strict models with user interfaces designed for those models and all their data. This design may not be ideal for every use case.

CMDBs also like to be authoritative for any data they possess. The problem with this in this day and age, very often other highly dedicated systems are the authoritative sources of lots and lots data, and these sources typically come with very domain specific scraping tools.

Via extensions you can tell Hubuum where to find your data, from as many sources as you like, and attach it to the same objects. Hubuum  provides a unified API to access this data, irrespective of its original source. You may have data coming from Active Directory, an MDM solution, automation tools, monitoring solutions, query tools (fleet/osquery/etc), or any other source, and you can use Hubuum to access all of it.

With hubuum you can...

- define your own data structures and their relationships.
- populate your data structures as JSON, and enforce validation when required.
- draw in data from any source into any object, structuring it as your organization requires.
- look up and search within these JSON structures in an efficient way, via a REST interface.
- offload the work of searching and indexing to Hubuum, and focus on your data.
- control permissions to one object set in one application instead of having to do it in multiple places.
- know that REST is your interface, no matter what data you are accessing.
  
Once upon a time your data was everywhere, each in its own silo. Now you can have it all in one place, and access it all through a single REST interface.
