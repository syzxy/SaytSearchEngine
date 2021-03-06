"""
Copyright 2019, University of Freiburg
Chair of Algorithms and Data Structures.
Hannah Bast <bast@cs.uni-freiburg.de>
Claudius Korzen <korzen@cs.uni-freiburg.de>
Patrick Brosi <brosi@cs.uni-freiburg.de>
"""

import readline  # NOQA
import sys
from collections import defaultdict

# Uncomment to use C version of prefix edit distance calculation.
# You have to install the module using the provided ped_c/setup.py
# first.
from ped_c import ped

# Comment to use C version of prefix edit distance calculation
#from ped_python import ped


class QGramIndex:
    """
    A QGram-Index.
    """

    def __init__(self, q):
        '''
        Creates an empty qgram index.
        '''

        self.q = q
        self.inverted_lists = defaultdict(list)  # The inverted lists.
        self.padding = "$" * (q - 1)
        self.entities = {}

    def build_from_file(self, file_name):
        '''
        Builds the index from the given file (one line per entity, see ES5).

        The entity IDs are one-based (starting with one).

        The test expects the index to store tuples (<entity id>, <frequency>),
        for each q-gram, where <entity id> is the ID of the entity the
        q-gram appears in, and <frequency> is the number of times it appears
        in the entity.

        For example, the 3-gram "rei" appears 1 time in entity 1 ("frei") and
        one time in entity 2 ("brei"), so its inverted list is
        [(1, 1), (2, 1)].

        >>> qi = QGramIndex(3)
        >>> qi.build_from_file("test.tsv")
        >>> sorted(qi.inverted_lists.items())
        ... # doctest: +NORMALIZE_WHITESPACE
        [('$$b', [(2, 1)]), ('$$f', [(1, 1)]), ('$br', [(2, 1)]),
         ('$fr', [(1, 1)]), ('bre', [(2, 1)]), ('fre', [(1, 1)]),
         ('rei', [(1, 1), (2, 1)])]
        '''
        # Code from lecture 5
        with open(file_name, "r") as file:
            next(file) # skip header
            entity_id = 0
            for line in file:
                if not line.strip():
                    continue
                entity_name, score, description, wiki_url, wiki_ID,\
                        synonyms, image_url = line.split("\t", 7)
                entity_id += 1
                self.entities[entity_id] = {
                        "name": entity_name,
                        "n_name": self.normalize(entity_name),
                        "score": score,
                        "desc": description,
                        "url": wiki_url,
                        "ID": wiki_ID,
                        "syn": synonyms.strip().split(';'),
                        "img": image_url
                        }
                for qgram in self.compute_qgrams(self.normalize(entity_name)):
                    if not self.inverted_lists[qgram] or entity_id != self.inverted_lists[qgram][-1][0]:
                        # If qgram is seen for the first time for a certain term, create new list.
                        self.inverted_lists[qgram].append((entity_id, 1))
                    else:
                        t, c = self.inverted_lists[qgram][-1]
                        c += 1
                        self.inverted_lists[qgram][-1] = t, c
    def normalize(self, word):
        '''
        Normalize the given string (remove non-word characters and lower case).

        >>> qi = QGramIndex(3)
        >>> qi.normalize("freiburg")
        'freiburg'
        >>> qi.normalize("Frei, burG !?!")
        'freiburg'
        '''

        low = word.lower()
        return ''.join([i for i in low if i.isalnum()])

    def compute_qgrams(self, word):
        '''
        Compute q-grams for padded version of given string,
        since the qgrams are used for computing prefix edit distance,
        only left paddings are added.

        >>> qi = QGramIndex(3)
        >>> qi.compute_qgrams("freiburg")
        ['$$f', '$fr', 'fre', 'rei', 'eib', 'ibu', 'bur', 'urg']
        '''
        w = self.padding + self.normalize(word)
        return [w[i: i+self.q] for i in range(len(w) - self.q + 1)]

    def merge_lists(self, lists):
        '''
        Merges the given inverted lists. The tests assume that the
        inverted lists keep count of the entity ID in the list,
        for example, in the first test below, entity 3 appears
        1 time in the first list, and 2 times in the second list.
        After the merge, it occurs 3 times in the merged list.

        >>> qi = QGramIndex(3)
        >>> qi.merge_lists([[(1, 2), (3, 1), (5, 1)],
        ...                 [(2, 1), (3, 2), (9, 2)]])
        [(1, 2), (2, 1), (3, 3), (5, 1), (9, 2)]
        >>> qi.merge_lists([[(1, 2), (3, 1), (5, 1)], []])
        [(1, 2), (3, 1), (5, 1)]
        >>> qi.merge_lists([[], []])
        []
        >>> qi.merge_lists([[(1, 1)], [(1, 1)], [(1, 1), (2, 1)]])
        [(1, 3), (2, 1)]
        '''
        tmp = []
        result = defaultdict(int)
        for l in lists:
            tmp += l
        for tID, frequency in tmp:
            result[tID] += frequency
        return sorted(result.items())

    def find_matches(self, prefix, delta):
        '''
        Finds all entities y with PED(x, y) <= delta for a given integer delta
        and a given (normalized) prefix x.

        The test checks for a list of triples containing the entity ID,
        the PED distance and its score:

        [(entity id, PED, score), ...]

        The entity IDs are one-based (starting with 1).

        >>> qi = QGramIndex(3)
        >>> qi.build_from_file("test.tsv")
        >>> qi.find_matches("frei", 0)
        [(1, 0, 3)]
        >>> qi.find_matches("frei", 2)
        [(1, 0, 3), (2, 1, 2)]
        >>> qi.find_matches("freibu", 2)
        [(1, 2, 3)]
        '''
        # 1. Fetch inverted lists of all q-grams generated by the input prefix
        q_grams = self.compute_qgrams(prefix)

        # 2. Merge all lists
        l = self.merge_lists(self.inverted_lists[g] for g in q_grams)

        # 3. Exclude terms that does not have enough q-grams in common with input prefix
        l = list(filter(lambda x: x[1] >= len(prefix)-self.q*delta, l))

        # 4. Compute prefix edit distance between the input prefix and remaning terms
        return [(tID, ped(prefix, self.entities[tID]["n_name"], delta), int(self.entities[tID]["score"]))
                for tID, _ in l if ped(prefix, self.entities[tID]["n_name"], delta) <= delta]

    def rank_matches(self, matches):
        '''
        Ranks the given list of (entity id, PED, s), where PED is the PED
        value and s is the popularity score of an entity.

        The test check for a list of triples containing the entity ID,
        the PED distance and its score:

        [(entity id, PED, score), ...]

        >>> qi = QGramIndex(3)
        >>> qi.rank_matches([(1, 0, 3), (2, 1, 2), (2, 1, 3), (1, 0, 2)])
        [(1, 0, 3), (1, 0, 2), (2, 1, 3), (2, 1, 2)]
        '''
        return sorted(matches, key=lambda x: (x[1], -x[2]))


if __name__ == "__main__":
    # Parse the command line arguments.
    if len(sys.argv) < 2:
        print("Usage: python3 %s <file>" % sys.argv[0])
        sys.exit()

    file_name = sys.argv[1]

    qi = QGramIndex(3)
    qi.build_from_file(file_name)
    while 1:
        query = qi.normalize(input("\nInput your query: "))
        print("\n" + "*" * 50)
        print(f"Your query after being normalised: {query}\n{len(query)//4} error(s) allowed")
        results = qi.rank_matches(qi.find_matches(query, len(query)//4))
        print("-" * 50)
        print(f"Results ({min(5, len(results))}/{len(results)}):")
        for i in range(min(5, len(results))):
            print(f'{i+1}. '+qi.entities[results[i][0]]['name']+'; '+qi.entities[results[i][0]]['desc']+'; '+qi.entities[results[i][0]]['url'])
        print("*" * 50)
