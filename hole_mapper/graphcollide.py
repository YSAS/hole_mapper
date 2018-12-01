from jbastro.great_circle_dist import dist_radec_fast
import numpy as np

class GraphCutError(Exception):
    pass

def build_overlap_graph_cartesian(x, y, d, overlap_pct_r_ok=0,
                                  allow_perfect=False):
    """
    Generate a dict of lists for crappy_min_vertex_cover_cut
    with edges between points that conflict
    
    Graph consists of a dict whos keys are indices into the lists passed
    and values which are also lists of indicies which conflict with
    
    
    set allowable overlap to something between 0  & 1.
    x----)(--y overlap of 0 for x or y
    x--(-)y overlaps for y by 1 radius and .5 for x
    default allowable_overlap
    
    allow_perfect allows overlap if position is exact match and diam is same
    
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
        neigh_mask=seps_sq < min_clearance**2
        if allow_perfect:
            perfect_match=(seps_sq==0) & (r[i]==r)
            neigh_mask=neigh_mask & ~perfect_match
            neigh=np.where(neigh_mask)[0].tolist()
        else:
            neigh=np.where(neigh_mask)[0].tolist()
            try:
                neigh.remove(i) #no connection to yourself
            except ValueError:
                import ipdb;ipdb.set_trace()
        assert i not in neigh

        if neigh: edges[i]=neigh

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

    def crappy_min_vertex_cover_cut(self, weights=None, ID='graph',
                                    retdrop=False, uncuttable=None):
        """
        Takes the number of nodes in the graph and a dict of lists
        keys into dict and node ids and the lists contain the ids of nodes
        to which edges exist
        
        lower node ids are given priority if a pair is isolated
        
        Returns the nodes in the disconnected graph
        
        
        Now for each star with a conflict there are a few cases
        We find the (potentially weighted) minimal vertex cover
          and drop it. Weights entirely override node rank e.g. a maximally 
          connected high priority node will cause all others to be dropped
        """
        from collections import OrderedDict
        from copy import deepcopy
        
        nodes=range(self._nnodes)
        #default to first node is most important
        if not weights: weights=[0]*self._nnodes

        if not uncuttable: uncuttable=[]

        edgegraph=deepcopy(self._graph)
        edgegraph=OrderedDict(edgegraph)
        
        single_drop_count=0
        multi_drop_count=0
#        try:
        dropped=[]
        while len(edgegraph) > 0:
            node,edge_set=edgegraph.popitem(last=False)
            #Case one, a pair of conflicting targets
            if len(edge_set)==1 and len(edgegraph[edge_set[0]])==1:
                assert node in edgegraph[edge_set[0]]
                #Drop the lower ranked of node and edges[node][0]
                # and remove them from the graph
                single_drop_count+=1
                
                if (node in uncuttable and
                    edge_set[0] in uncuttable):
                    raise GraphCutError('Connected nodes both in uncuttable. '
                                        'Error at node {}'.format(node))
                
                if ((weights[node] < weights[edge_set[0]] and
                     node not in uncuttable) or
                    edge_set[0] in uncuttable):
                    to_drop=node
                    edgegraph.pop(edge_set[0])
                else:
                    to_drop=edge_set[0]
                    edge_set=edgegraph.pop(edge_set[0])
            
                #Drop the node
                nodes.remove(to_drop)
                dropped.append((to_drop, edge_set))

        
            #Case 2, a set of 3 or more conflicting targets
            else:
                multi_drop_count+=1
                #Node is connected to multiple others drop
                #Want a weighted minimum vertex cover.
                #instead go for a greedy variant
                #drop lowest weighted node with most connections
                
                edgegraph[node]=edge_set
                to_drop=self._walk_return_dropnode(edgegraph, node,
                                                   edge_set, weights,
                                                   uncuttable)
                if to_drop==None:
                    raise GraphCutError('Connected nodes all uncuttable.'
                                        'Error at node {}'.format(node))
                
                edge_set=edgegraph.pop(to_drop)

                #Drop the node
                nodes.remove(to_drop)
                dropped.append((to_drop, edge_set))
                
                #Cull all the node's edges from the graph
                for node2 in edge_set:
                    if len(edgegraph[node2]) == 1:
                        edgegraph.pop(node2)
                    else:
                        edgegraph[node2].remove(to_drop)

#        except Exception, e:
#            print str(e)
#            import ipdb;ipdb.set_trace()

        #Make sure we weren't overzelous
        if dropped:
            #Sort dropped by weight and try to add them back
            dropped=[(d, weights[d[0]]) for d in dropped]
            dropped.sort(key=lambda x:x[1], reverse=True)
            dropped=[d[0] for d in dropped]
            
            for node, edges in dropped:
                #None of edges are in nodes
                if not len([n for n in edges if n in nodes]):
                    print "Added back a node"
                    nodes.append(node)

#        if multi_drop_count >0:
#            print "Warning: Dropped {} multi-overlapping stars in {}".format(
#                        multi_drop_count,ID)
#        

        if retdrop:
            drop=[i for i in range(self._nnodes) if i not in nodes]
            return nodes, drop
        else:
            return nodes

    def _walk_return_dropnode(self, edgegraph, start, edges, weights,
                              uncuttable):
        """walk the graph connected to start and return the node having min
            weight and most edges of min weights"""
        visited=[]
        to_visit=set(edges)

        if start in uncuttable:
            minw=float('inf')
        else:
            minw=weights[start]
        rank=len(edges)
        to_drop=start
        
        while to_visit:
            current=to_visit.pop()
            try:
                current_edges=edgegraph[current]
            except KeyError:
                import ipdb;ipdb.set_trace()
            visited.append(current)
            
            #add new points to to_visit
            to_visit.update([e for e in current_edges if e not in visited])

            if current not in uncuttable:
                #Select the current node for removal if lower weight
                # or same weight and more connections
                if weights[current] < minw:
                    minw=weights[current]
                    to_drop=current
                elif weights[current]==minw and len(current_edges)> rank:
                    to_drop=current
    
        if to_drop in uncuttable:
            to_drop=None
        return to_drop

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
    
    def get_colliding_nodes(self):
        return self._graph.keys()

    @property
    def is_disconnected(self):
        return not self._graph

        
    