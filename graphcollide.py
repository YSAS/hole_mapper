from jbastro.great_circle_dist import dist_radec_fast
import numpy as np


def build_overlap_graph_cartesian(x, y, d, overlap_pct_r_ok=0):
    """
    Generate a dict of lists for crappy_min_vertex_cover_cut
    with edges between points that conflict
    
    Graph consists of a dict whos keys are indices into the lists passed
    and values which are also lists of indicies which conflict with
    
    
    set allowable overlap to something between 0  & 1.
    x----)(--y overlap of 0 for x or y
    x--(-)y overlaps for y by 1 radius and .5 for x
    default allowable_overlap
    
    may generate conntions that only go one direction
    """
    edges={}
    x=np.array(x)
    y=np.array(y)
    r=np.array(d)/2.0
    hole_radii_set=set(r.tolist())
    
    for i,coord in enumerate(zip(x,y)):
        xx,yy=coord
        seps_sq=(x-xx)**2+(y-yy)**2
        neighbors=[]
        min_clearance=r+r[i]*(1-overlap_pct_r_ok)
        neigh=np.where(seps_sq < min_clearance**2)[0].tolist()
        try:
            neigh.remove(i) #no connection to yourself
        except ValueError:
            import ipdb;ipdb.set_trace()
        if neigh:
            edges[i]=neigh
    
    for k in edges.keys():
        for other in edges[k]:
            if other not in edges:
                edges[other]=[k]
            elif k not in edges[other]:
                edges[other].append(k)

    return CollisionGraph(len(x), edges)


def build_proximity_graph(ra, dec, overlap_sep):
    """
    Generate a dict of lists for crappy_min_vertex_cover_cut
    with edges between points closer than overlap_sep degrees
    
    ra and dec are arrays of coordinates in degrees
    """
    edges={}
    for node, cord in enumerate(zip(ra,dec)):
        seps=dist_radec_fast(cord[0], cord[1], ra, dec,
                             method='Haversine', unit='deg',
                             scale=overlap_sep)
        neighbors=np.where( seps < overlap_sep )[0].tolist()
        neighbors.remove(node) #no connection to yourself
        if len(neighbors)!=0:
            edges[node]=neighbors
    return CollisionGraph(len(ra), edges)


class CollisionGraph(object):
    def __init__(self, nnodes, edgegraph):
        
        #Verify graph is properly constructed
        self._nnodes=nnodes
        self._graph=edgegraph

        self.verify()

    def verify(self):
        """Verify graph is properly formed"""
    
        for i in self._graph:
            assert i < self._nnodes
            edges=self._graph[i]
            assert edges!=[]
            for e in edges:
                assert e in self._graph
                assert i in self._graph[e]

    def crappy_min_vertex_cover_cut(self, weights=None, ID='graph', retdrop=False):
        """
        Takes the number of nodes in the graph and a dict of lists
        keys into dict and node ids and the lists contain the ids of nodes
        to which edges exist
        
        lower node ids are given priority if a pair is isolated
        
        Returns the nodes in the disconnected graph
        
        
        Now for each star with a conflict there are a few cases
        Ideally we would find the (potentially weighted) minimal vertex cover
          and drop it, but that is getting all fancy and graph theoretic
        """
        from collections import OrderedDict
        from copy import deepcopy
        
        nodes=range(self._nnodes)
        #default to first node is most important
        if not weights:
            weights=[self._nnodes - i for i in nodes]

        
        edgegraph=deepcopy(self._graph)
        edgegraph=OrderedDict(edgegraph)
        
        single_drop_count=0
        multi_drop_count=0
        try:
            while len(edgegraph) > 0:
                node,edge_set=edgegraph.popitem(last=False)
                #Case one, a pair of conflicting targets
                if len(edge_set)==1 and len(edgegraph[edge_set[0]])==1:
                    assert node in edgegraph[edge_set[0]]
                    #Drop the lower ranked of node and edges[node][0]
                    # and remove them from the graph
                    single_drop_count+=1
                    nodes.remove(node if weights[node] < weights[edge_set[0]]
                                      else edge_set[0])
                    edgegraph.pop(edge_set[0])
                #Case 2, a set of 3 or more conflicting targets
                else:
                    if len(edge_set)>1:
                        multi_drop_count+=1
                        nodes.remove(node)
                        for node2 in edge_set:
                            if len(edgegraph[node2]) == 1:
                                edgegraph.pop(node2)
                            else:
                                edgegraph[node2].remove(node)
                    else: #this is an end node
                        edgegraph[node]=edge_set
        except Exception, e:
            print str(e)
            import ipdb;ipdb.set_trace()
        
        if multi_drop_count >0:
            print "Warning: Dropped {} multi-overlapping stars in {}".format(
                        multi_drop_count,ID)
        
        
        
        if retdrop:
            drop=[i for i in range(self._nnodes) if i not in nodes]
            return nodes,drop
        else:
            return nodes

    def drop(self, node):
        """ Remove node from graph, return all nodes that conflicted with it """

        to_keep=self._graph.pop(node,[])
        for i in to_keep:
            self._graph[i].remove(node)
    
        #prune isolated
        for k,v in self._graph.items():
            if not v:
                self._graph.pop(k)

        self.verify()
        return to_keep

    def drop_conflicting_with(self, node):
        """ Remove and return all nodes having conflicts with node """
        to_drop=self._graph.pop(node,[])
        for i in to_drop:
            toupdate=self._graph.pop(i)
            toupdate.remove(node)
            for j in toupdate:
                self._graph[j].remove(i)

        #prune isolated
        for k,v in self._graph.items():
            if not v:
                self._graph.pop(k)
        self.verify()
        return to_drop

    def collisions(self, node):
        try:
            return list(self._graph[node])
        except:
            return []

    def get_colliding_node(self):
        return self._graph.keys()[0]

    @property
    def is_disconnected(self):
        return not self._graph

        
    