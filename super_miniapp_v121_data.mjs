// V12.1: static, offline, non-AI question and puzzle packs. No account data.
export const ACTIVITIES = [
 ['quick-quiz','study','⚡','Quick Quiz','விரைவு வினாடி வினா','ඉක්මන් ප්‍රශ්න'],
 ['flashcard-sprint','study','🗂️','Flashcard Sprint','நினைவட்டைப் பயிற்சி','මතක කාඩ්පත්'],
 ['mcq-challenge','study','📝','MCQ Challenge','பல்தேர்வு சவால்','බහුවරණ අභියෝගය'],
 ['match-pairs','study','🔗','Match the Pairs','இணைகளைப் பொருத்து','යුගල ගැළපීම'],
 ['fill-blanks','study','✍️','Fill in the Blanks','விடுபட்ட சொற்கள்','හිස්තැන් පුරවන්න'],
 ['sentence-builder','study','🔤','Sentence Builder','வாக்கிய அமைப்பு','වාක්‍ය ගොඩනැගීම'],
 ['spelling-bee','study','🐝','Spelling Bee','எழுத்துப்பிழை சவால்','අක්ෂර වින්‍යාසය'],
 ['math-race','study','➕','Math Race','கணிதப் போட்டி','ගණිත තරඟය'],
 ['formula-match','study','📐','Formula Match','சூத்திரப் பொருத்தம்','සූත්‍ර ගැළපීම'],
 ['science-challenge','study','🔬','Science Challenge','அறிவியல் சவால்','විද්‍යා අභියෝගය'],
 ['geography-quiz','study','🌍','Geography Quiz','புவியியல் வினாடி வினா','භූගෝල ප්‍රශ්න'],
 ['timeline-challenge','study','📅','Timeline Challenge','காலவரிசை சவால்','කාලරේඛා අභියෝගය'],
 ['memory-flip','mind','🧠','Memory Flip','நினைவு அட்டைகள்','මතක යුගල'],
 ['sequence-recall','mind','🎵','Sequence Recall','வரிசை நினைவாற்றல்','අනුක්‍රම මතකය'],
 ['sudoku','mind','🔢','Sudoku','சுடோகு','සුඩෝකු'],
 ['2048','mind','🧩','2048 Puzzle','2048 புதிர்','2048 ප්‍රහේලිකාව'],
 ['sliding-puzzle','mind','⬜','Sliding Puzzle','நகர்த்தும் புதிர்','ලිස්සන ප්‍රහේලිකාව'],
 ['word-search','mind','🔎','Word Search','சொல் தேடல்','වචන සෙවීම'],
 ['number-patterns','mind','🔁','Number Patterns','எண் வரிசைகள்','සංඛ්‍යා රටා'],
 ['maze-escape','mind','🧭','Maze Escape','பிரமை வழி','වංකගිරිය'],
 ['make-24','mind','🎯','Make 24','24 உருவாக்கு','24 සාදන්න'],
 ['logic-grid','mind','🕵️','Logic Grid','தர்க்கப் புதிர்','තර්ක ප්‍රහේලිකාව'],
 ['observation','mind','👁️','Observation Challenge','கவனிப்பு சவால்','නිරීක්ෂණ අභියෝගය'],
 ['reaction','mind','⚡','Reaction Challenge','எதிர்வினை சவால்','ප්‍රතික්‍රියා අභියෝගය'],
 ['exam-countdown','helper','⏳','Exam Countdown','தேர்வு நாள் கணிப்பு','විභාග දින ගණනය'],
 ['spaced-repetition','helper','🗓️','Spaced Repetition','இடைவெளி மீள்பார்வை','කාලාන්තර පුනරීක්ෂණය'],
 ['topic-wheel','helper','🎡','Revision Topic Wheel','தலைப்பு தேர்வு','මාතෘකා තේරීම'],
 ['question-builder','helper','📋','Practice Question Builder','வினா உருவாக்கி','ප්‍රශ්න සාදන්නා'],
 ['streak-calendar','helper','🔥','Study Streak Calendar','படிப்பு தொடர் நாட்கள்','අධ්‍යයන අඛණ්ඩතාව'],
 ['study-estimator','helper','🧮','Study Load Estimator','படிப்பு நேரக் கணிப்பு','අධ්‍යයන කාල ගණනය'],
 ['scorecard-export','helper','📊','Scorecard Export','மதிப்பெண் பதிவிறக்கம்','ලකුණු වාර්තාව'],
 ['daily-scheduler','helper','🗓️','Daily Study Scheduler','தினசரி படிப்பு அட்டவணை','දෛනික අධ්‍යයන සැලසුම'],
].map(([id,category,emoji,en,ta,si])=>({id,category,emoji,name:{en,ta,si}}));

export const LABELS={
 en:{title:'Study & Mind Games Arcade',subtitle:'Practice, play and track your progress.',back:'← Back to Super Mini App',study:'Study Games',mind:'Mind Games',helper:'Study Helpers',all:'All',search:'Search games or tools…',plays:'Rounds played',best:'Best score',points:'Total XP',start:'Start',check:'Check',next:'Next',restart:'Play again',save:'Save',clear:'Clear',answer:'Answer',submit:'Submit',correct:'Correct!',wrong:'Try again',done:'Completed!',local:'Scores are stored only on this device. No leaderboard or account upload.',language:'Language',home:'All games',score:'Score',skip:'Skip',hint:'Hint',new:'New challenge',show:'Show answer',close:'Close',share:'Share',download:'Download',time:'Time',results:'Results',easy:'Easy',medium:'Medium',hard:'Hard',reset:'Reset progress',confirm:'Delete the local Arcade progress and activity records on this device?',noGames:'No matching activities.',instructions:'Instructions',ready:'Ready',nextCard:'Next card',remembered:'Remembered',again:'Practice again',undo:'Undo',shuffle:'Shuffle',days:'Days',minutes:'Minutes',topic:'Topic',add:'Add',remove:'Remove',export:'Export',private:'Nothing is uploaded automatically.',offline:'No AI API needed. Some built-in questions are in English.'},
 ta:{title:'கற்றல் மற்றும் சிந்தனை விளையாட்டுகள்',subtitle:'பயிற்சி செய், விளையாடு, முன்னேற்றத்தைப் பார்.',back:'← முதன்மை செயலிக்குச் செல்',study:'கற்றல் விளையாட்டுகள்',mind:'மன விளையாட்டுகள்',helper:'கற்றல் உதவிகள்',all:'அனைத்தும்',search:'விளையாட்டுகளைத் தேடு…',plays:'விளையாடிய சுற்றுகள்',best:'சிறந்த மதிப்பெண்',points:'மொத்த புள்ளிகள்',start:'தொடங்கு',check:'சரிபார்',next:'அடுத்து',restart:'மீண்டும் விளையாடு',save:'சேமி',clear:'அழி',answer:'பதில்',submit:'சமர்ப்பி',correct:'சரி!',wrong:'மீண்டும் முயற்சி',done:'முடிந்தது!',local:'மதிப்பெண்கள் இந்தச் சாதனத்தில் மட்டும் சேமிக்கப்படும்.',language:'மொழி',home:'அனைத்து விளையாட்டுகள்',score:'மதிப்பெண்',skip:'தவிர்',hint:'குறிப்பு',new:'புதிய சவால்',show:'பதில் காட்டு',close:'மூடு',share:'பகிர்',download:'பதிவிறக்கு',time:'நேரம்',results:'முடிவுகள்',easy:'எளிது',medium:'நடுத்தரம்',hard:'கடினம்',reset:'முன்னேற்றத்தை அழி',confirm:'இந்தச் சாதனத்தில் சேமிக்கப்பட்ட முன்னேற்றத்தை அழிக்கவா?',noGames:'பொருந்தும் விளையாட்டுகள் இல்லை.',instructions:'வழிமுறைகள்',ready:'தயார்',nextCard:'அடுத்த அட்டை',remembered:'நினைவில் உள்ளது',again:'மீண்டும் பயிற்சி',undo:'மீளமை',shuffle:'கலக்கு',days:'நாட்கள்',minutes:'நிமிடங்கள்',topic:'தலைப்பு',add:'சேர்',remove:'நீக்கு',export:'ஏற்றுமதி',private:'தானாக எந்தத் தரவும் பதிவேற்றப்படாது.',offline:'AI தேவையில்லை. சில உள்ளடக்கங்கள் ஆங்கிலத்தில் உள்ளன.'},
 si:{title:'ඉගෙනුම් හා මනස පුහුණු ක්‍රීඩා',subtitle:'ඉගෙන ගන්න, ක්‍රීඩා කරන්න, ප්‍රගතිය බලන්න.',back:'← ප්‍රධාන යෙදුමට',study:'ඉගෙනුම් ක්‍රීඩා',mind:'මනස පුහුණු ක්‍රීඩා',helper:'අධ්‍යයන මෙවලම්',all:'සියල්ල',search:'ක්‍රීඩා සොයන්න…',plays:'ක්‍රීඩා වාර',best:'හොඳම ලකුණු',points:'මුළු XP',start:'ආරම්භය',check:'පරීක්ෂා කරන්න',next:'ඊළඟ',restart:'නැවත ක්‍රීඩා',save:'සුරකින්න',clear:'මකන්න',answer:'පිළිතුර',submit:'යොමු කරන්න',correct:'නිවැරදියි!',wrong:'නැවත උත්සාහ කරන්න',done:'අවසන්!',local:'ලකුණු මේ උපාංගයේ පමණක් සුරැකේ.',language:'භාෂාව',home:'සියලු ක්‍රීඩා',score:'ලකුණු',skip:'මඟ හරින්න',hint:'ඉඟිය',new:'අලුත් අභියෝගය',show:'පිළිතුර පෙන්වන්න',close:'වසන්න',share:'බෙදාගන්න',download:'බාගන්න',time:'වේලාව',results:'ප්‍රතිඵල',easy:'පහසු',medium:'මධ්‍යම',hard:'අමාරු',reset:'ප්‍රගතිය මකන්න',confirm:'මෙම උපාංගයේ ප්‍රගතිය මකන්නද?',noGames:'ගැලපෙන ක්‍රීඩා නැත.',instructions:'උපදෙස්',ready:'සූදානම්',nextCard:'ඊළඟ කාඩ්පත',remembered:'මතකයි',again:'නැවත පුහුණු වන්න',undo:'අවලංගු',shuffle:'මිශ්‍ර කරන්න',days:'දින',minutes:'මිනිත්තු',topic:'මාතෘකාව',add:'එකතු කරන්න',remove:'ඉවත් කරන්න',export:'අපනයනය',private:'දත්ත ස්වයංක්‍රීයව උඩුගත නොවේ.',offline:'AI අවශ්‍ය නැත. සමහර ප්‍රශ්න ඉංග්‍රීසි භාෂාවෙනි.'}
};
export const quizBanks={
 general:[
 ['What is 12 × 8?',['80','96','108','88'],1,'12 × 8 = 96.'],['How many sides does a hexagon have?',['5','6','8','10'],1,'Hexa means six.'],['What is the square root of 81?',['7','9','8','6'],1,'9 × 9 = 81.'],['Which planet is known as the Red Planet?',['Venus','Mars','Jupiter','Earth'],1,'Mars looks reddish because of iron oxide.'],['Which gas do plants take in during photosynthesis?',['Oxygen','Nitrogen','Carbon dioxide','Helium'],2,'Plants use carbon dioxide with water and sunlight.'],['What is 25% of 200?',['25','50','75','100'],1,'A quarter of 200 is 50.'],['Which is a prime number?',['21','27','29','33'],2,'29 has only two factors.'],['How many minutes are in 2.5 hours?',['120','135','150','160'],2,'2.5 × 60 = 150.']
 ],
 science:[
 ['What is the chemical formula of water?',['H2O','CO2','O2','NaCl'],0,'Two hydrogen atoms and one oxygen atom.'],['Which organ pumps blood?',['Liver','Heart','Lungs','Kidney'],1,'The heart circulates blood.'],['What force keeps us on Earth?',['Friction','Gravity','Magnetism','Electricity'],1,'Gravity pulls objects toward Earth.'],['Which state has a fixed volume but no fixed shape?',['Solid','Liquid','Gas','Plasma'],1,'A liquid takes the shape of its container.'],['What is the SI unit of electric current?',['Volt','Ohm','Ampere','Watt'],2,'Electric current is measured in amperes.'],['DNA stands for?',['Deoxyribonucleic acid','Direct nitrogen acid','Double nucleus atom','Data network array'],0,'DNA stores genetic information.']
 ],
 geography:[
 ['What is the capital of Sri Lanka?',['Colombo','Sri Jayawardenepura Kotte','Kandy','Galle'],1,'Sri Jayawardenepura Kotte is the administrative capital.'],['Which country has the capital Tokyo?',['China','Japan','South Korea','Thailand'],1,'Tokyo is Japan’s capital.'],['Which country has the capital Canberra?',['Australia','Canada','Austria','New Zealand'],0,'Canberra is Australia’s capital.'],['What is the capital of India?',['Mumbai','Chennai','New Delhi','Kolkata'],2,'New Delhi is the capital of India.'],['Which continent has Egypt?',['Europe','Asia','Africa','South America'],2,'Most of Egypt is in Africa.'],['What is the largest ocean?',['Atlantic','Indian','Pacific','Arctic'],2,'The Pacific Ocean is the largest.'],['What is the capital of Nepal?',['Kathmandu','Thimphu','Dhaka','Lahore'],0,'Kathmandu is Nepal’s capital.']
 ],
 patterns:[
 ['2, 4, 8, 16, ?', ['24','30','32','36'],2,'Each number doubles.'],['3, 6, 9, 12, ?', ['14','15','16','18'],1,'Add 3 each time.'],['1, 4, 9, 16, ?', ['20','25','24','30'],1,'Consecutive squares.'],['5, 10, 20, 40, ?', ['50','60','80','100'],2,'Multiply by 2.'],['1, 1, 2, 3, 5, ?', ['6','8','10','9'],1,'Fibonacci: add the previous two.']
 ]
};
export const cards=[['Photosynthesis','Plants convert light energy to chemical energy.'],['Mitochondria','Organelles involved in producing ATP.'],['Fraction','A part of a whole.'],['Prime number','An integer greater than 1 with exactly two positive divisors.'],['Evaporation','Liquid changes into gas.'],['Gravity','Attraction between masses.'],['Metaphor','A comparison without like or as.'],['Equator','Imaginary line at 0° latitude.']];
export const blanks=[['The chemical symbol for gold is ___.','Au'],['The square root of 64 is ___.','8'],['Water freezes at ___ °C under standard pressure.','0'],['A triangle has ___ sides.','3'],['Plants release ___ during photosynthesis.','oxygen']];
export const sentences=['Learning makes us stronger','Practice helps improve memory','The Earth moves around the Sun','Students can learn through games'];
export const spelling=[['Study of living organisms','biology'],['A four-sided shape with equal sides','square'],['The pull that keeps objects on Earth','gravity'],['The process plants use to make food','photosynthesis'],['A number with two factors','prime']];
export const formulas=[['Area of a rectangle','length × width'],['Circumference of a circle','2 × π × radius'],['Speed','distance ÷ time'],['Simple interest','principal × rate × time ÷ 100'],['Density','mass ÷ volume'],['Area of a triangle','½ × base × height']];
export const historic=[['First modern Olympic Games',1896],['World War I begins',1914],['United Nations founded',1945],['First person walks on the Moon',1969],['World Wide Web publicly available',1991]];
export const logicPuzzles=[
 {intro:'Ali, Bea and Chen each chose a different fruit (apple, banana, mango).',clues:['Ali did not choose mango or apple.','Bea did not choose apple.'],people:['Ali','Bea','Chen'],items:['Apple','Banana','Mango'],solution:['Banana','Mango','Apple']},
 {intro:'Dana, Evan and Faye each chose a different subject (Math, Art, Music).',clues:['Dana chose neither Art nor Music.','Faye did not choose Art.'],people:['Dana','Evan','Faye'],items:['Math','Art','Music'],solution:['Math','Art','Music']}
];
