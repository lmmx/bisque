from collections import defaultdict

__all__ = ["TreeBuilderRegistry"]


class TreeBuilderRegistry:
    """A way of looking up TreeBuilder subclasses by their name or by desired
    features.
    """

    def __init__(self):
        self.builders_for_feature = defaultdict(list)
        self.builders = []

    def register(self, treebuilder_class):
        """Register a treebuilder based on its advertised features.

        :param treebuilder_class: A subclass of Treebuilder. its .features
           attribute should list its features.
        """
        for feature in treebuilder_class.features:
            self.builders_for_feature[feature].insert(0, treebuilder_class)
        self.builders.insert(0, treebuilder_class)

    def lookup(self, *features):
        """Look up a TreeBuilder subclass with the desired features.

        :param features: A list of features to look for. If none are
            provided, the most recently registered TreeBuilder subclass
            will be used.
        :return: A TreeBuilder subclass, or None if there's no
            registered subclass with all the requested features.
        """
        if len(self.builders) == 0:
            # There are no builders at all.
            return None

        if len(features) == 0:
            # They didn't ask for any features. Give them the most
            # recently registered builder.
            return self.builders[0]

        # Go down the list of features in order, and eliminate any builders
        # that don't match every feature.
        features = list(features)
        features.reverse()
        candidates = None
        candidate_set = None
        while len(features) > 0:
            feature = features.pop()
            we_have_the_feature = self.builders_for_feature.get(feature, [])
            if len(we_have_the_feature) > 0:
                if candidates is None:
                    candidates = we_have_the_feature
                    candidate_set = set(candidates)
                else:
                    # Eliminate any candidates that don't have this feature.
                    candidate_set = candidate_set.intersection(set(we_have_the_feature))

        # The only valid candidates are the ones in candidate_set.
        # Go through the original list of candidates and pick the first one
        # that's in candidate_set.
        if candidate_set is None:
            return None
        for candidate in candidates:
            if candidate in candidate_set:
                return candidate
        return None
