#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright: (c) 2013, Jared Suttles. All rights reserved.
# License: See LICENSE for details.
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - 

"""
Tokenization and pre-processing for social media data used to train classifiers.
Focused on classification of sentiment, emotion, or mood.

Intended as glue between Python wrappers for Twitter API and the Natural 
Language Toolkit (NLTK), but probably applicable to tokenizing any short 
messages of the social networking variety.

In many cases, reducing feature-set complexity can increase performance of 
classifiers trained for detecting sentiment. The available settings are based 
on commonly modified and normalized features in classification research using 
content from Twitter.
"""

import re
from os import path
try:
    from itertools import imap
except ImportError:
    imap = map
from htmlentitydefs import name2codepoint

class Tokenizer(object):
    """
    Can be used to tokenize a string representation of a message, adjusting 
    features based on the given configuration details, to enable further 
    processing in feature extraction and training stages.
    
    An example usage::
    
      >>> from tweetokenize import Tokenizer
      >>> gettokens = Tokenizer(usernames='USER', urls='')
      >>> gettokens.tokenize('@justinbeiber yo man!love you#inlove#wantyou in a totally straight way #brotime <3:p:D www.justinbeiber.com')
      [u'USER', u'yo', u'man', u'!', u'love', u'you', u'#inlove', u'#wantyou', u'in', u'a', u'totally', u'straight', u'way', u'#brotime', u'<3', u':p', u':D']
    """
    class TokenizerException(BaseException):
        pass
    html_entities = {k:unichr(v) for k,v in name2codepoint.items()}
    __default_args = None

    # Regular expressions
    usernames_re = re.compile(r"@\w{1,15}")
    _topleveldomains = 'museum|travel|aero|arpa|asia|coop|info|jobs|mobi|name|post|biz|cat|com|edu|gov|int|mil|net|org|pro|tel|xxx|ac|ad|ae|af|ag|ai|al|am|an|ao|aq|ar|as|at|au|aw|ax|az|ba|bb|bd|be|bf|bg|bh|bi|bj|bm|bn|bo|br|bs|bt|bv|bw|by|bz|ca|cc|cd|cf|cg|ch|ci|ck|cl|cm|cn|co|cr|cu|cv|cw|cx|cy|cz|de|dj|dk|dm|do|dz|ec|ee|eg|er|es|et|eu|fi|fj|fk|fm|fo|fr|ga|gb|gd|ge|gf|gg|gh|gi|gl|gm|gn|gp|gq|gr|gs|gt|gu|gw|gy|hk|hm|hn|hr|ht|hu|id|ie|il|im|in|io|iq|ir|is|it|je|jm|jo|jp|ke|kg|kh|ki|km|kn|kp|kr|kw|ky|kz|la|lb|lc|li|lk|lr|ls|lt|lu|lv|ly|ma|mc|md|me|mg|mh|mk|ml|mm|mn|mo|mp|mq|mr|ms|mt|mu|mv|mw|mx|my|mz|na|nc|ne|nf|ng|ni|nl|no|np|nr|nu|nz|om|pa|pe|pf|pg|ph|pk|pl|pm|pn|pr|ps|pt|pw|py|qa|re|ro|rs|ru|rw|sa|sb|sc|sd|se|sg|sh|si|sj|sk|sl|sm|sn|so|sr|st|su|sv|sx|sy|sz|tc|td|tf|tg|th|tj|tk|tl|tm|tn|to|tp|tr|tt|tv|tw|tz|ua|ug|uk|us|uy|uz|va|vc|ve|vg|vi|vn|vu|wf|ws|ye|yt|za|zm|zw'
    urls_re = re.compile(r"(?:(?:https?\://[A-Za-z0-9\.]+)|(?:(?:www\.)?[A-Za-z0-9]+\.(?:%s)))(?:\/\S+)?(?=\s+|$)" % _topleveldomains)
    hashtags_re = re.compile(r"#\w+[\w'-]*\w+")
    ellipsis_re = re.compile(r"\.\.+")
    word_re = re.compile(r"(?:[a-zA-Z0-9]+['-]?[a-zA-Z]+[a-zA-Z0-9]*)|(?:[a-zA-Z0-9]*[a-zA-Z]+['-]?[a-zA-Z0-9]+)")
    times_re = re.compile(r"\d{1,2}:\d{2}(?::\d{2})?\s*(?:AM|PM|am|pm)?")
    phonenumbers_re = re.compile(r"(?:\+?[01][\-\s\.]*)?(?:\(?\d{3}[\-\s\.\)]*)?\d{3}[\-\s\.]*\d{4}(?:\s*x\s*\d+)?(?=\s+|$)")
    _number = r"(?:[+-]?\$?\d+(?:\.\d+)?(?:[eE]-?\d+)?%?)(?![A-Za-z])"
    numbers_re = re.compile(r"%(num)s(?:\s*/\s*%(num)s)?" % {'num': _number}) # deals with fractions
    other_re = r"(?:[^#\s\.]|\.(?!\.))+"
    _token_regexs = ('usernames', 'urls', 'hashtags', 'times', 'phonenumbers', 'numbers')
    tokenize_re = re.compile(ur"|".join(imap(lambda x: getattr(x, 'pattern', x),
        [locals()['%s_re' % regex] for regex in _token_regexs] + [word_re, ellipsis_re, other_re])))
    del regex  # otherwise stays in class namespace
    html_entities_re = re.compile(r"&#?\w+;")
    repeating_re = re.compile(r"([a-zA-Z])\1\1+")
    _doublequotes = ((u'“',u'”'),(u'"',u'"'),(u'‘',u'’'),(u'＂',u'＂'))
    punctuation = (u'!$%()*+,-/:;<=>?[\\]^_.`{|}~\'' + u''.join(c for t in _doublequotes for c in t))
    quotes_re = re.compile(ur"|".join(ur'(%s.*?%s)' % t for t in _doublequotes) + ur'|\s(\'.*?\')\s')

    def __init__(self, lowercase=True, allcapskeep=True, normalize=3,
                 usernames='USERNAME', urls='URL', hashtags=False,
                 phonenumbers='PHONENUMBER', times='TIME', numbers='NUMBER',
                 ignorequotes=False, ignorestopwords=False):
        """
        Constructs a new Tokenizer. Can specify custom settings for various 
        feature normalizations.
        
        Any features with replacement tokens can be removed from the message by 
        setting the token to the empty string (C{""}), C{"DELETE"}, or 
        C{"REMOVE"}.
        
        @type lowercase: C{bool}
        @param lowercase: If C{True}, lowercases words, excluding those with 
            all letters capitalized.
        
        @type allcapskeep: C{bool}
        @param allcapskeep: If C{True}, maintains capitalization for words with 
            all letters in capitals. Otherwise, capitalization for such words 
            is dependent on C{lowercase}.
        
        @type normalize: C{int}
        @param normalize: The number of repeating letters when normalizing 
            arbitrary letter elongations.
            
            Example::
                Heyyyyyy i lovvvvvvve youuuuuuuuu <3
            
            Becomes::
                Heyyy i lovvve youuu <3
            
            Not sure why you would want to change this (maybe just for fun?? :P)
        
        @param usernames: Serves as the replacement token for anything that 
            parses as a Twitter username, ie. C{@rayj}. Setting this to 
            C{False} means no usernames will be changed.
        
        @param urls: Serves as the replacement token for anything that 
            parses as a URL, ie. C{bit.ly} or C{http://example.com}. Setting 
            this to C{False} means no URLs will be changed.
        
        @param hashtags: Serves as the replacement token for anything that 
            parses as a Twitter hashtag, ie. C{#ihititfirst} or 
            C{#onedirection}. Setting this to C{False} means no hashtags will 
            be changed.
        
        @param phonenumbers: Replacement token for phone numbers.
        
        @param times: Replacement token for times.
        
        @param numbers: Replacement token for any other kinds of numbers.
        
        @type ignorequotes: C{bool}
        @param ignorequotes: If C{True}, will remove various types of quotes 
            and the contents within.
        
        @type ignorestopwords: C{bool}
        @param ignorestopwords: If C{True}, will remove any stopwords. The 
            default set includes 'I', 'me', 'itself', 'against', 'should', etc.
        """
        if self.__default_args is None:
            self.__default_args = locals().keys()
        for keyword, value in locals().items():
            setattr(self, keyword, value)
        lexicons = path.dirname(path.realpath(__file__)) + '/lexicons/%s.txt'
        self.emoticons(filename=lexicons % 'emoticons')
        self.stopwords(filename=lexicons % 'stopwords')

    def __call__(self, iterable):
        """
        Iterator for the tokenization of given messages.
        
        @rtype: C{list} of C{str}
        @return: Iterator of lists representing message tokenizations.
        
        @param iterable: Object capable of iteration, providing strings for 
            tokenization.
        """
        for msg in iterable:
            yield self.tokenize(msg)

    def update(self, **kwargs):
        """
        Adjust any settings of the Tokenizer.
        
          >>> gettokens.lowercase
          True
          >>> gettokens.phonenumbers
          'PHONENUMBER'
          >>> gettokens.update(phonenumbers='NUMBER', lowercase=False)
          >>> gettokens.lowercase
          False
          >>> gettokens.phonenumbers
          'NUMBER'
        """
        for keyword in self.__default_args:
            if keyword in kwargs:
                setattr(self, keyword, kwargs[keyword])

    def _converthtmlentities(self, msg):
        def replace_entities(s):
            s = s.group(0)[1:-1] # remove & and ;
            if s[0] == '#':
                try:
                    return unichr(int(s[2:],16) if s[1] in 'xX' else int(s[1:]))
                except ValueError:
                    return '&#' + s + ';'
            else:
                try:
                    return self.html_entities[s]
                except KeyError:
                    return '&' + s + ';'
        return self.html_entities_re.sub(replace_entities, msg)

    def _replacetokens(self, msg):
        tokens = []; deletion_tokens = ('','REMOVE','remove','DELETE','delete')
        for word in msg:
            matching = self.word_re.match(word) # 1st check if normal word
            if matching and len(matching.group(0)) == len(word):
                tokens.append(self._cleanword(word))
                continue # don't check rest of conditions
            for token in self._token_regexs: # id & possibly replace tokens
                regex = getattr(Tokenizer, '%s_re' % token)
                replacementtoken = getattr(self, token)
                if regex.match(word):
                    if replacementtoken: # decide if we change it
                        word = self._unicode(str(replacementtoken))
                    if replacementtoken not in deletion_tokens:
                        tokens.append(word)
                    break
            else: # we didn't find a match for any token so far...
                if self.ellipsis_re.match(word):
                    tokens.append(u"...")
                else: # split into tokens based on emoticons or punctuation
                    tokens.extend(self._separate_emoticons_punctuation(word))
        return tokens

    def _separate_emoticons_punctuation(self, word):
        newwords=[]; wordbefore=u""; i=0
        def possibly_append_and_reset(w):
            if w:
                newwords.append(self._cleanword(w))
            return u""
        while i < len(word):
            # greedily check for emoticons in this word
            for l in range(self._maxlenemo, 0, -1):
                if word[i:i+l] in self._emoticons or self._isemoji(word[i:i+l]):
                    wordbefore = possibly_append_and_reset(wordbefore)
                    newwords.append(word[i:i+l])
                    i+=l
                    break
            else: # its safe to break up any punctuation not part of emoticons
                if word[i] in self.punctuation:
                    wordbefore = possibly_append_and_reset(wordbefore)
                    newwords.append(word[i])
                else:
                    wordbefore += word[i]
                i+=1
        # possible ending of word which wasn't emoticon or punctuation
        possibly_append_and_reset(wordbefore)
        return newwords

    def _isemoji(self, s):
        emoji_ranges = ((u'\U0001f300', u'\U0001f5ff'), (u'\U0001f600', u'\U0001f64f'),
                        (u'\U0001f680', u'\U0001f6c5'), (u'\u2600', u'\u26ff'), (u'\U0001f170', u'\U0001f19a'))
        emoji_flags =  {u'\U0001f1ef\U0001f1f5', u'\U0001f1f0\U0001f1f7', u'\U0001f1e9\U0001f1ea',
                        u'\U0001f1e8\U0001f1f3', u'\U0001f1fa\U0001f1f8', u'\U0001f1eb\U0001f1f7',
                        u'\U0001f1ea\U0001f1f8', u'\U0001f1ee\U0001f1f9', u'\U0001f1f7\U0001f1fa',
                        u'\U0001f1ec\U0001f1e7'}
        check_emoji = lambda given: len(given) == len(u'\U0001f4a9') and any(l <= given <= u for l,u in emoji_ranges)
        return check_emoji(s) or s in emoji_flags

    def _cleanword(self, word):
        if self.normalize: # replace characters with >=3 alphabetic repeating
            word = self.repeating_re.sub(r"\1"*self.normalize, word)
        if self.lowercase and (not self.allcapskeep or not word.isupper()):
            return word.lower()
        return word

    def _unicode(self, word):
        if isinstance(word, unicode):
            return word
        return unicode(word, encoding='utf-8')

    def tokenize(self, message):
        """
        Tokenize the given string into a list of strings representing the 
        constituent words of the message.
        
        @rtype: C{list} of C{str}
        @return: The tokenization of the message.
        
        @type message: C{str}
        @param message: The string representation of the message.
        """
        if not isinstance(message, basestring):
            raise self.TokenizerException('cannot tokenize non-string, %s'
            % repr(message.__class__.__name__))
        message = self._converthtmlentities(self._unicode(message))
        if self.ignorequotes:
            message = self.quotes_re.sub(" ", message)
        message = self._replacetokens(self.tokenize_re.findall(message))
        if self.ignorestopwords:
            message = [word for word in message if word not in self._stopwords]
        return message

    def emoticons(self, iterable=None, filename=None):
        """
        Consumes an iterable of emoticons that the tokenizer will tokenize on. 
        Allows for user-specified set of emoticons to be recognized.
        
        @param iterable: Object capable of iteration, providing emoticon 
            strings.
        @type filename: C{str}
        @param filename: Path to the file containing emoticons delimited by 
            new lines. Strips trailing whitespace and skips blank lines.
        """
        self._emoticons = self._collectset(iterable, filename)
        self._maxlenemo = max(len(max(self._emoticons, key=lambda x: len(x))),
        len(u'\U0001f1e8\U0001f1f3'), len(u'\U0001f48b'))

    def stopwords(self, iterable=None, filename=None):
        """
        Consumes an iterable of stopwords that the tokenizer will ignore if the 
        stopwords setting is C{True}. The default set is taken from NLTK's 
        english list.
        
        @param iterable: Object capable of iteration, providing stopword 
            strings.
        @type filename: C{str}
        @param filename: Path to the file containing stopwords delimited by 
            new lines. Strips trailing whitespace and skips blank lines.
        """
        self._stopwords = self._collectset(iterable, filename)

    def _collectset(self, iterable, filename):
        if filename:
            with open(filename, "r") as f:
                iterable = set(l.rstrip() for l in f)
                iterable.discard('')
        return set(imap(self._unicode, iterable))
