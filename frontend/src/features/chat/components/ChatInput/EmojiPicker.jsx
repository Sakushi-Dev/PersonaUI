// ── EmojiPicker ──
// Categorized emoji popup for the chat input

import { useState, useRef, useEffect, useCallback } from 'react';
import styles from './EmojiPicker.module.css';
import { getEmojiUsage, incrementEmojiUsage } from '../../../../services/emojiApi';

// ── Emoji keyword map for search (EN only) ──
const EMOJI_KEYWORDS = {
  '😀':'grin smile happy','😃':'grin smile happy','😄':'laugh smile happy grin',
  '😁':'grin beam smile','😆':'laugh xd squint','😅':'sweat smile nervous',
  '🤣':'rofl rolling floor laugh','😂':'tears joy laugh cry','🙂':'smile slight',
  '🙃':'upside down irony','😉':'wink','😊':'blush smile shy',
  '😇':'angel halo innocent','🥰':'love hearts adore','😍':'heart eyes love',
  '🤩':'starstruck stars excited wow','😘':'kiss heart blow','😗':'kiss','😚':'kiss closed eyes',
  '😙':'kiss whistle','🥲':'smile tear sad happy','😋':'yummy tongue delicious',
  '😛':'tongue out','😜':'tongue wink crazy','🤪':'crazy zany wild',
  '😝':'tongue squint','🤑':'money dollar rich','🤗':'hug warm embrace',
  '🤭':'giggle hand mouth','🫢':'oops hand mouth surprised','🤫':'shush quiet secret',
  '🤔':'thinking hmm wonder','🫡':'salute','🤐':'zipper mouth silent',
  '🤨':'raised eyebrow skeptical','😐':'neutral blank','😑':'expressionless annoyed',
  '😶':'mouthless silent','🫥':'dotted faded invisible','😏':'smirk sly',
  '😒':'unamused bored annoyed','🙄':'eye roll annoyed','😬':'grimacing awkward',
  '🤥':'lying pinocchio nose','😌':'relieved content','😔':'sad pensive thoughtful',
  '😪':'sleepy tear','🤤':'drool hungry','😴':'sleep zzz tired',
  '😷':'mask sick','🤒':'sick fever thermometer','🤕':'hurt head bandage injured',
  '🤢':'nauseous sick green','🤮':'vomit puke throw up','🥴':'woozy drunk dizzy',
  '😵':'dizzy faint','🤯':'mind blown exploding head','🥳':'party celebration birthday',
  '🥸':'disguise glasses incognito','😎':'cool sunglasses','🤓':'nerd glasses geek',
  '🧐':'monocle inspect smart','😕':'confused uncertain','🫤':'diagonal skeptical uncertain',
  '😟':'worried concerned','🙁':'frown sad unhappy','😮':'surprised open mouth oh',
  '😯':'hushed wow amazed','😲':'astonished shocked','😳':'flushed embarrassed red',
  '🥺':'pleading puppy eyes beg','🥹':'holding back tears emotional touched','😦':'frowning open mouth',
  '😧':'anguished worried','😨':'fearful scared afraid','😰':'anxious sweat cold',
  '😥':'sad relieved','😢':'cry tear sad','😭':'sobbing loud cry wail',
  '😱':'scream horror fear','😖':'confounded frustrated','😣':'persevere endure',
  '😞':'disappointed sad','😓':'downcast sweat','😩':'weary tired',
  '😫':'tired exhausted','🥱':'yawn bored tired','😤':'triumph steam angry huff',
  '😡':'angry red rage furious','😠':'angry mad','🤬':'swearing cursing symbols',
  '😈':'devil evil purple','👿':'devil evil angry imp','💀':'skull dead death',
  '☠️':'skull crossbones pirate','💩':'poop shit','🤡':'clown joker',
  '👹':'oni monster demon','👺':'tengu goblin mask','👻':'ghost halloween boo',
  '👽':'alien ufo extraterrestrial','👾':'space invader monster pixel','🤖':'robot bot machine',
  '👋':'wave hello bye goodbye','🤚':'raised hand stop halt','🖐️':'hand fingers five spread',
  '✋':'hand stop high five','🖖':'spock vulcan trek','🫱':'hand right',
  '🫲':'hand left','🫳':'hand down palm','🫴':'hand up palm',
  '👌':'ok okay perfect nice','🤌':'pinch italian fingertips','🤏':'tiny small pinch little',
  '✌️':'peace victory two','🤞':'crossed fingers luck','🫰':'money snap love',
  '🤟':'love you sign language','🤘':'rock horns metal','🤙':'call me hang loose shaka',
  '👈':'left point','👉':'right point','👆':'up point',
  '🖕':'middle finger','👇':'down point','☝️':'up point one index',
  '🫵':'point you','👍':'thumbs up like good yes','👎':'thumbs down dislike bad no',
  '✊':'fist raised power','👊':'fist punch bump','🤛':'left fist bump',
  '🤜':'right fist bump','👏':'clap applause bravo','🙌':'raise hands celebration hooray',
  '🫶':'heart hands love','👐':'open hands','🤲':'palms up please',
  '🤝':'handshake deal agreement','🙏':'pray please thank you namaste','✍️':'writing hand',
  '💅':'nail polish manicure','🤳':'selfie photo camera','💪':'muscle strong biceps flex',
  '🦾':'mechanical arm prosthetic robot','🦿':'mechanical leg prosthetic robot','🦵':'leg knee',
  '🦶':'foot toes','👂':'ear listen hear','🦻':'hearing aid ear',
  '👃':'nose smell sniff','🧠':'brain think smart','🫀':'heart organ anatomical',
  '🫁':'lungs breath','🦷':'tooth dentist','🦴':'bone skeleton',
  '👀':'eyes look see watch','👁️':'eye gaze','👅':'tongue lick',
  '👄':'mouth lips kiss','🫦':'lip bite',
  '❤️':'heart red love','🧡':'heart orange','💛':'heart yellow',
  '💚':'heart green','💙':'heart blue','💜':'heart purple',
  '🖤':'heart black','🤍':'heart white','🤎':'heart brown',
  '💔':'broken heart sad','❤️‍🔥':'heart fire burning','❤️‍🩹':'heart mending repair healing',
  '❣️':'heart exclamation','💕':'two hearts love','💞':'revolving hearts spinning',
  '💓':'beating heart pulse','💗':'growing heart','💖':'sparkling heart glitter',
  '💘':'heart arrow cupid','💝':'heart ribbon gift','💟':'heart decoration',
  '💌':'love letter mail envelope',
  '💋':'kiss lips','💍':'ring diamond engagement wedding','💎':'diamond gem jewel gemstone',
  '🐶':'dog puppy','🐱':'cat kitten','🐭':'mouse','🐹':'hamster',
  '🐰':'rabbit bunny','🦊':'fox','🐻':'bear','🐼':'panda bear',
  '🐻‍❄️':'polar bear','🐨':'koala bear','🐯':'tiger','🦁':'lion king',
  '🐮':'cow','🐷':'pig','🐸':'frog','🐵':'monkey',
  '🙈':'see no evil monkey','🙉':'hear no evil monkey','🙊':'speak no evil monkey',
  '🐒':'monkey','🐔':'chicken hen','🐧':'penguin','🐦':'bird',
  '🐤':'chick baby','🐣':'hatching chick','🐥':'chick front','🦆':'duck quack',
  '🦅':'eagle','🦉':'owl','🦇':'bat','🐺':'wolf',
  '🐗':'boar wild pig','🐴':'horse','🦄':'unicorn magical','🐝':'bee honey',
  '🪱':'worm','🐛':'bug caterpillar','🦋':'butterfly','🐌':'snail',
  '🐞':'ladybug','🐜':'ant','🪰':'fly','🪲':'beetle',
  '🪳':'cockroach','🦟':'mosquito','🦗':'cricket','🕷️':'spider',
  '🦂':'scorpion','🐢':'turtle','🐍':'snake','🦎':'lizard gecko',
  '🐙':'octopus','🦑':'squid','🦞':'lobster','🦀':'crab',
  '🐡':'blowfish puffer','🐠':'tropical fish','🐟':'fish','🐬':'dolphin',
  '🐳':'whale','🐋':'whale blue','🦈':'shark','🐊':'crocodile alligator',
  '🐅':'tiger','🐆':'leopard','🦓':'zebra','🦍':'gorilla ape',
  '🦧':'orangutan','🐘':'elephant','🦛':'hippo hippopotamus',
  '🍏':'apple green','🍎':'apple red','🍐':'pear','🍊':'orange tangerine',
  '🍋':'lemon sour','🍌':'banana','🍉':'watermelon','🍇':'grapes wine',
  '🍓':'strawberry','🫐':'blueberry','🍈':'melon honeydew','🍒':'cherry',
  '🍑':'peach','🥭':'mango','🍍':'pineapple','🥥':'coconut',
  '🥝':'kiwi','🍅':'tomato','🍆':'eggplant aubergine','🥑':'avocado',
  '🫛':'pea green pod','🥦':'broccoli','🥬':'lettuce greens','🥒':'cucumber',
  '🌶️':'chili pepper hot spicy','🫑':'bell pepper','🌽':'corn','🥕':'carrot',
  '🫒':'olive','🧄':'garlic','🧅':'onion','🥔':'potato',
  '🍠':'sweet potato','🫘':'beans','🥐':'croissant','🍞':'bread loaf',
  '🥖':'baguette french bread','🥨':'pretzel','🧀':'cheese','🥚':'egg',
  '🍳':'fried egg','🧈':'butter','🥞':'pancake','🧇':'waffle',
  '🥓':'bacon','🥩':'steak meat','🍗':'chicken drumstick leg','🍖':'meat bone ribs',
  '🌭':'hotdog sausage','🍔':'burger hamburger cheeseburger','🍟':'fries french fries',
  '🍕':'pizza','🫓':'flatbread','🥪':'sandwich','🥙':'pita kebab wrap',
  '🧆':'falafel','🌮':'taco mexican','🌯':'burrito wrap','🫔':'tamale',
  '🥗':'salad bowl','🍝':'spaghetti pasta noodles','🍜':'ramen noodle soup','🍲':'stew pot',
  '🍛':'curry','🍣':'sushi','🍱':'bento box japanese','🥟':'dumpling',
  '🦪':'oyster shell','🍤':'shrimp prawn','🍙':'onigiri rice ball','🍚':'rice bowl',
  '🍘':'rice cracker','🍥':'narutomaki fish cake','🥠':'fortune cookie','🥮':'moon cake',
  '🍢':'oden skewer','🍡':'dango sweet','🍧':'shaved ice','🍨':'ice cream sundae',
  '🍦':'soft ice cream cone','🥧':'pie','🧁':'cupcake muffin','🍰':'cake slice shortcake',
  '🎂':'birthday cake','🍮':'pudding flan custard','🍭':'lollipop candy',
  '🍬':'candy sweet','🍫':'chocolate bar','🍿':'popcorn cinema','🍩':'donut doughnut',
  '🍪':'cookie biscuit','🌰':'chestnut nut','🥜':'peanut nut','🍯':'honey pot',
  '☕':'coffee tea hot drink','🍵':'tea cup','🧋':'bubble tea boba','🥤':'cup drink straw',
  '🍶':'sake','🍺':'beer mug','🍻':'beer cheers clink','🥂':'champagne cheers clink toast',
  '🍷':'wine red glass','🥃':'whiskey tumbler','🍸':'cocktail martini','🍹':'tropical cocktail drink',
  '🧉':'mate','🍾':'champagne bottle pop','🧊':'ice cube',
  '⌚':'watch time clock','📱':'phone smartphone mobile','💻':'laptop computer notebook',
  '⌨️':'keyboard','🖥️':'monitor desktop computer screen','🖨️':'printer',
  '🖱️':'mouse computer','🖲️':'trackball','💾':'floppy disk save',
  '💿':'cd disk','📷':'camera photo','📹':'video camera','🎥':'film camera cinema',
  '📞':'phone receiver','☎️':'telephone','📡':'satellite dish antenna',
  '🔋':'battery power','🔌':'plug power electric','💡':'lightbulb idea',
  '🔦':'flashlight torch','🕯️':'candle','🪔':'lamp oil diya',
  '🧯':'fire extinguisher','💰':'money bag cash','💳':'credit card payment',
  '⚖️':'scale justice balance','🔧':'wrench tool',
  '🔨':'hammer tool','⚒️':'hammer pick tool','🛠️':'tools hammer wrench',
  '⛏️':'pickaxe mining','🔩':'nut bolt screw','⚙️':'gear settings cog',
  '🧲':'magnet','🔫':'gun water pistol','💣':'bomb','🪓':'axe wood chop',
  '🗡️':'dagger sword','⚔️':'swords crossed battle fight','🏹':'bow arrow archery',
  '🛡️':'shield','🪃':'boomerang','🔮':'crystal ball magic fortune',
  '📿':'prayer beads','🧿':'evil eye nazar amulet','💈':'barber pole',
  '🔬':'microscope','🔭':'telescope','🩺':'stethoscope doctor',
  '🩹':'bandage plaster','💊':'pill medicine drug','🧬':'dna gene',
  '🦠':'virus microbe germ bacteria','🧪':'test tube lab','🧫':'petri dish lab',
  '🧹':'broom sweep','🪣':'bucket pail','🧺':'basket laundry',
  '🧻':'toilet paper roll','🚽':'toilet restroom','🪠':'plunger',
  '🚿':'shower','🛁':'bathtub bath','🪤':'mousetrap trap',
  '🪒':'razor shave','🧴':'lotion bottle','🧽':'sponge',
  '📚':'books read stack','📖':'book open read','🔖':'bookmark',
  '📎':'paperclip','✂️':'scissors cut','🖊️':'pen ballpoint',
  '✒️':'ink pen nib','🖋️':'fountain pen','✏️':'pencil','📐':'triangle ruler',
  '📏':'ruler straight edge',
  '⭐':'star','🌟':'star glowing bright','✨':'sparkles glitter shine',
  '⚡':'lightning zap energy bolt','🔥':'fire hot flame','💫':'dizzy shooting star',
  '🎉':'party popper confetti celebrate','🎊':'confetti ball celebration','🎈':'balloon party','🎁':'gift present wrapped',
  '🏆':'trophy winner cup','🏅':'medal sport achievement','🥇':'gold first place',
  '🥈':'silver second place','🥉':'bronze third place','⚽':'soccer football',
  '🏀':'basketball','🏈':'football american','⚾':'baseball','🥎':'softball',
  '🎾':'tennis','🏐':'volleyball','🏉':'rugby','🎱':'billiards pool eight ball',
  '🔔':'bell notification alert','🎵':'music note','🎶':'music notes melody',
  '🎤':'microphone sing karaoke','🎧':'headphones music listen','🎸':'guitar',
  '🎹':'piano keyboard music','🎺':'trumpet','🎷':'saxophone','🥁':'drum',
  '🎯':'target dart bullseye','♠️':'spade card suit',
  '♦️':'diamond card suit','♣️':'club card suit','🃏':'joker wild card',
  '🀄':'mahjong','🎲':'dice game','🧩':'puzzle piece','♟️':'chess pawn',
  '✅':'check mark green yes done','❌':'cross mark no wrong','❓':'question mark',
  '❗':'exclamation mark important','⚠️':'warning caution alert','🚫':'prohibited no banned',
  '♻️':'recycling','✳️':'asterisk star','❇️':'sparkle','🔆':'bright high',
  '🔅':'dim low','⭕':'circle red hollow','🔴':'red circle','🟠':'orange circle',
  '🟡':'yellow circle','🟢':'green circle','🔵':'blue circle',
  '🟣':'purple circle','⚫':'black circle','⚪':'white circle',
  '🟤':'brown circle','🔶':'orange diamond large','🔷':'blue diamond large',
  '🔸':'orange diamond small','🔹':'blue diamond small',
};

// Build a flat search index: emoji → lowercase keywords
const ALL_EMOJIS = [];
const EMOJI_SEARCH_INDEX = new Map();

const EMOJI_CATEGORIES = [
  {
    name: 'Smileys',
    icon: '😀',
    emojis: [
      '😀','😃','😄','😁','😆','😅','🤣','😂','🙂','🙃',
      '😉','😊','😇','🥰','😍','🤩','😘','😗','😚','😙',
      '🥲','😋','😛','😜','🤪','😝','🤑','🤗','🤭','🫢',
      '🤫','🤔','🫡','🤐','🤨','😐','😑','😶','🫥','😏',
      '😒','🙄','😬','🤥','😌','😔','😪','🤤','😴','😷',
      '🤒','🤕','🤢','🤮','🥴','😵','🤯','🥳','🥸','😎',
      '🤓','🧐','😕','🫤','😟','🙁','😮','😯','😲','😳',
      '🥺','🥹','😦','😧','😨','😰','😥','😢','😭','😱',
      '😖','😣','😞','😓','😩','😫','🥱','😤','😡','😠',
      '🤬','😈','👿','💀','☠️','💩','🤡','👹','👺','👻',
      '👽','👾','🤖',
    ],
  },
  {
    name: 'Gesten',
    icon: '👋',
    emojis: [
      '👋','🤚','🖐️','✋','🖖','🫱','🫲','🫳','🫴','👌',
      '🤌','🤏','✌️','🤞','🫰','🤟','🤘','🤙','👈','👉',
      '👆','🖕','👇','☝️','🫵','👍','👎','✊','👊','🤛',
      '🤜','👏','🙌','🫶','👐','🤲','🤝','🙏','✍️','💅',
      '🤳','💪','🦾','🦿','🦵','🦶','👂','🦻','👃','🧠',
      '🫀','🫁','🦷','🦴','👀','👁️','👅','👄','🫦',
    ],
  },
  {
    name: 'Herzen',
    icon: '❤️',
    emojis: [
      '❤️','🧡','💛','💚','💙','💜','🖤','🤍','🤎','💔',
      '❤️‍🔥','❤️‍🩹','❣️','💕','💞','💓','💗','💖','💘','💝',
      '💟','♥️','🫶','💌','💋','💍','💎',
    ],
  },
  {
    name: 'Tiere',
    icon: '🐱',
    emojis: [
      '🐶','🐱','🐭','🐹','🐰','🦊','🐻','🐼','🐻‍❄️','🐨',
      '🐯','🦁','🐮','🐷','🐸','🐵','🙈','🙉','🙊','🐒',
      '🐔','🐧','🐦','🐤','🐣','🐥','🦆','🦅','🦉','🦇',
      '🐺','🐗','🐴','🦄','🐝','🪱','🐛','🦋','🐌','🐞',
      '🐜','🪰','🪲','🪳','🦟','🦗','🕷️','🦂','🐢','🐍',
      '🦎','🐙','🦑','🦞','🦀','🐡','🐠','🐟','🐬','🐳',
      '🐋','🦈','🐊','🐅','🐆','🦓','🦍','🦧','🐘','🦛',
    ],
  },
  {
    name: 'Essen',
    icon: '🍕',
    emojis: [
      '🍏','🍎','🍐','🍊','🍋','🍌','🍉','🍇','🍓','🫐',
      '🍈','🍒','🍑','🥭','🍍','🥥','🥝','🍅','🍆','🥑',
      '🫛','🥦','🥬','🥒','🌶️','🫑','🌽','🥕','🫒','🧄',
      '🧅','🥔','🍠','🫘','🥐','🍞','🥖','🥨','🧀','🥚',
      '🍳','🧈','🥞','🧇','🥓','🥩','🍗','🍖','🌭','🍔',
      '🍟','🍕','🫓','🥪','🥙','🧆','🌮','🌯','🫔','🥗',
      '🍝','🍜','🍲','🍛','🍣','🍱','🥟','🦪','🍤','🍙',
      '🍚','🍘','🍥','🥠','🥮','🍢','🍡','🍧','🍨','🍦',
      '🥧','🧁','🍰','🎂','🍮','🍭','🍬','🍫','🍿','🍩',
      '🍪','🌰','🥜','🍯','☕','🍵','🧋','🥤','🍶','🍺',
      '🍻','🥂','🍷','🥃','🍸','🍹','🧉','🍾','🧊',
    ],
  },
  {
    name: 'Objekte',
    icon: '💡',
    emojis: [
      '⌚','📱','💻','⌨️','🖥️','🖨️','🖱️','🖲️','💾','💿',
      '📷','📹','🎥','📞','☎️','📡','🔋','🔌','💡','🔦',
      '🕯️','🪔','🧯','💰','💳','💎','⚖️','🔧','🔨','⚒️',
      '🛠️','⛏️','🔩','⚙️','🧲','🔫','💣','🪓','🗡️','⚔️',
      '🏹','🛡️','🪃','🔮','📿','🧿','💈','🔬','🔭','📡',
      '🩺','🩹','💊','🧬','🦠','🧪','🧫','🧹','🪣','🧺',
      '🧻','🚽','🪠','🚿','🛁','🪤','🪒','🧴','🧽','📚',
      '📖','🔖','📎','✂️','🖊️','✒️','🖋️','✏️','📐','📏',
    ],
  },
  {
    name: 'Symbole',
    icon: '⭐',
    emojis: [
      '⭐','🌟','✨','⚡','🔥','💫','🎉','🎊','🎈','🎁',
      '🏆','🏅','🥇','🥈','🥉','⚽','🏀','🏈','⚾','🥎',
      '🎾','🏐','🏉','🎱','🔔','🎵','🎶','🎤','🎧','🎸',
      '🎹','🎺','🎷','🥁','🎯','♠️','♥️','♦️','♣️','🃏',
      '🀄','🎲','🧩','♟️','✅','❌','❓','❗','⚠️','🚫',
      '♻️','✳️','❇️','🔆','🔅','⭕','🔴','🟠','🟡','🟢',
      '🔵','🟣','⚫','⚪','🟤','🔶','🔷','🔸','🔹',
    ],
  },
];

// Build the search index from categories + keyword map
EMOJI_CATEGORIES.forEach((cat) => {
  cat.emojis.forEach((emoji) => {
    if (!ALL_EMOJIS.includes(emoji)) ALL_EMOJIS.push(emoji);
    const kw = (EMOJI_KEYWORDS[emoji] || '') + ' ' + cat.name.toLowerCase();
    EMOJI_SEARCH_INDEX.set(emoji, kw.toLowerCase());
  });
});


// Favorites persisted via backend API (file-based)
const MAX_FAVO = 24;

function deriveFavorites(usage) {
  return Object.entries(usage)
    .sort((a, b) => b[1] - a[1])
    .slice(0, MAX_FAVO)
    .map(([emoji]) => emoji);
}


export default function EmojiPicker({ onSelect, visible, onClose }) {
  const [activeCategory, setActiveCategory] = useState('favo');
  const [favoriteEmojis, setFavoriteEmojis] = useState([]);
  const [search, setSearch] = useState('');
  const panelRef = useRef(null);
  const gridRef = useRef(null);
  const usageRef = useRef({});

  // Close on outside click
  useEffect(() => {
    if (!visible) return;
    const handleClickOutside = (e) => {
      if (panelRef.current && !panelRef.current.contains(e.target)) {
        const toggleBtn = e.target.closest('[data-emoji-toggle]');
        if (!toggleBtn) {
          onClose();
        }
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [visible, onClose]);

  // Close on Escape
  useEffect(() => {
    if (!visible) return;
    const handleKey = (e) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handleKey);
    return () => document.removeEventListener('keydown', handleKey);
  }, [visible, onClose]);

  const handleEmojiClick = useCallback((emoji) => {
    // Optimistic local update
    usageRef.current[emoji] = (usageRef.current[emoji] || 0) + 1;
    setFavoriteEmojis(deriveFavorites(usageRef.current));
    onSelect(emoji);
    // Persist to file via API (fire-and-forget)
    incrementEmojiUsage(emoji).catch(() => {});
  }, [onSelect]);

  // Load favorites from API when opening
  useEffect(() => {
    if (visible) {
      setSearch('');
      getEmojiUsage()
        .then((res) => {
          const usage = res.usage || {};
          usageRef.current = usage;
          setFavoriteEmojis(deriveFavorites(usage));
        })
        .catch(() => {});
    }
  }, [visible]);

  // Scroll grid to top when category changes
  useEffect(() => {
    if (gridRef.current) {
      gridRef.current.scrollTop = 0;
    }
  }, [activeCategory]);

  if (!visible) return null;


  // Determine which emojis to show
  let displayEmojis;
  let displayTitle;

  if (search.trim()) {
    const q = search.trim().toLowerCase();
    displayEmojis = ALL_EMOJIS.filter((e) => {
      const kw = EMOJI_SEARCH_INDEX.get(e) || '';
      return kw.includes(q);
    });
    displayTitle = 'Suchergebnisse';
  } else if (activeCategory === 'favo') {
    displayEmojis = favoriteEmojis;
    displayTitle = 'Favoriten';
  } else {
    displayEmojis = EMOJI_CATEGORIES[activeCategory].emojis;
    displayTitle = EMOJI_CATEGORIES[activeCategory].name;
  }

  return (
    <div className={styles.panel} ref={panelRef}>
      {/* Search */}
      <div className={styles.searchRow}>
        <input
          className={styles.searchInput}
          type="text"
          placeholder="Emoji suchen..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          autoFocus
        />
      </div>

      {/* Category tabs */}
      <div className={styles.categories}>
        <button
          className={`${styles.catBtn} ${styles.favoTab} ${activeCategory === 'favo' && !search ? styles.catActive : ''}`}
          onClick={() => { setActiveCategory('favo'); setSearch(''); }}
          title="Favoriten"
          type="button"
        >
          ★
        </button>
        {EMOJI_CATEGORIES.map((cat, i) => (
          <button
            key={cat.name}
            className={`${styles.catBtn} ${activeCategory === i && !search ? styles.catActive : ''}`}
            onClick={() => { setActiveCategory(i); setSearch(''); }}
            title={cat.name}
            type="button"
          >
            {cat.icon}
          </button>
        ))}
      </div>

      {/* Category title */}
      {!search && <div className={styles.catTitle}>{displayTitle}</div>}

      {/* Emoji grid */}
      <div className={styles.grid} ref={gridRef}>
        {displayEmojis.length === 0 ? (
          <div className={styles.empty}>
            {activeCategory === -1 ? 'Noch keine Emojis verwendet' : 'Keine Emojis gefunden'}
          </div>
        ) : (
          displayEmojis.map((emoji, i) => (
            <button
              key={`${emoji}-${i}`}
              className={styles.emojiBtn}
              onClick={() => handleEmojiClick(emoji)}
              type="button"
              title={emoji}
            >
              {emoji}
            </button>
          ))
        )}
      </div>
    </div>
  );
}
