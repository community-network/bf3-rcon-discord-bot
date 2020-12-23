import struct

CLIENT_SEQ_NR = 0

def EncodeHeader(isFromServer, isResponse, sequence):
    header = sequence & 0x3fffffff
    if isFromServer:
        header += 0x80000000
    if isResponse:
        header += 0x40000000
    return struct.pack('<I', header).decode()

def DecodeHeader(data):
    data = data.encode()
    [header] = struct.unpack('<I', data[0 : 4])
    return [header & 0x80000000, header & 0x40000000, header & 0x3fffffff]

def EncodeInt32(size):
    return struct.pack('<I', size).decode()

def DecodeInt32(data):
    return struct.unpack('<I', data[0 : 4].encode('windows-1252'))[0]

def EncodeWords(words):
    size = 0
    encodedWords = u''
    for word in words:
        strWord = str(word)
        encodedWords += EncodeInt32(len(strWord))
        encodedWords += strWord
        encodedWords += u'\x00'
        size += len(strWord) + 5
    return size, encodedWords

def DecodeWords(size, data):
    numWords = DecodeInt32(data[0:])
    words = []
    offset = 0
    while offset < size:
        wordLen = DecodeInt32(data[offset : offset + 4])
        word = data[offset + 4 : offset + 4 + wordLen]
        words.append(word)
        offset += wordLen + 5

    return words

def EncodePacket(isFromServer, isResponse, sequence, words):
    encodedHeader = EncodeHeader(isFromServer, isResponse, sequence)
    encodedNumWords = EncodeInt32(len(words))
    [wordsSize, encodedWords] = EncodeWords(words)
    encodedSize = EncodeInt32(wordsSize + 12)
    return encodedHeader + encodedSize + encodedNumWords + encodedWords

def DecodePacket(data):
    [isFromServer, isResponse, sequence] = DecodeHeader(data)
    wordsSize = DecodeInt32(data[4:8]) - 12
    words = DecodeWords(wordsSize, data[12:])
    return [isFromServer, isResponse, sequence, words]

def EncodeClientRequest(words):
    global CLIENT_SEQ_NR
    packet = EncodePacket(False, False, CLIENT_SEQ_NR, words)
    orig_seq = CLIENT_SEQ_NR

    CLIENT_SEQ_NR = (CLIENT_SEQ_NR + 1) & 0x3fffffff

    return packet, orig_seq

def EncodeClientResponse(sequence, words):
    return EncodePacket(True, True, sequence, words)

def containsCompletePacket(data):
    if len(data) < 8:
        return False
    if len(data) < DecodeInt32(data[4:8]):
        return False
    return True