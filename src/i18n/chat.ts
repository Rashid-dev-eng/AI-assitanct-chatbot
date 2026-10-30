import type { ChatLanguage } from '../types/chat';

export const chatCopy = {
  en: {
    welcome: 'What can I help you with?',
    status: 'Preview assistant · no live DeLMS records',
    suggestions: ['What can you help me with?', 'Find learning materials', 'How do I access my courses?'],
    placeholder: 'Type your message...',
    working: 'Checking reviewed DeLMS guidance…',
    assignment: 'I can provide general assignment guidance, but the exact DeLMS submission steps need to come from a reviewed DMI source.',
    quiz: 'I can help with general quiz navigation, but I need a reviewed DMI source for exact DeLMS instructions.',
    fallback: 'I can chat and help with general DeLMS navigation topics such as courses and learning materials. Exact institutional instructions require reviewed sources.',
    clarify: 'Which DeLMS section do you mean—My Courses, Learning Materials, Assignments, Quizzes, Grades, Messages, or account help?',
    noTranslation: 'I do not have a reviewed {language} equivalent for “{term}”. I have not invented one.',
    proposedTranslation: 'Proposed, unverified {language} wording for “{term}”: “{translation}”. This is not an approved DMI translation.',
    proposedOnly: 'I found a proposed phrase association for “{term}”, but no reviewed {language} equivalent. The phrase has not been validated by DMI.',
    verifiedTranslation: 'Reviewed {language} equivalent for “{term}”: “{translation}”.',
  },
  sw: {
    welcome: 'Ninaweza kukusaidia vipi?',
    status: 'Msaidizi wa majaribio · hakuna rekodi za moja kwa moja',
    suggestions: ['Unaweza kunisaidia nini?', 'Tafuta vifaa vya kujifunzia', 'Ninawezaje kufikia kozi zangu?'],
    placeholder: 'Andika ujumbe wako...',
    working: 'Inatafuta maelekezo ya DeLMS yaliyokaguliwa…',
    assignment: 'Ninaweza kutoa mwongozo wa jumla kuhusu kazi, lakini hatua sahihi za kuwasilisha kwenye DeLMS zinahitaji chanzo cha DMI kilichokaguliwa.',
    quiz: 'Ninaweza kusaidia kuhusu urambazaji wa jumla wa majaribio, lakini maelekezo sahihi ya DeLMS yanahitaji chanzo cha DMI kilichokaguliwa.',
    fallback: 'Ninaweza kuzungumza na kusaidia kuhusu mada za jumla za DeLMS kama kozi na vifaa vya kujifunzia. Maelekezo rasmi yanahitaji vyanzo vilivyokaguliwa.',
    clarify: 'Unaulizia sehemu gani ya DeLMS—My Courses, Learning Materials, Assignments, Quizzes, Grades, Messages, au akaunti?',
    noTranslation: 'Sina tafsiri ya {language} iliyokaguliwa ya “{term}”. Sijabuni tafsiri.',
    proposedTranslation: 'Pendekezo la {language} ambalo halijathibitishwa la “{term}”: “{translation}”. Hii si tafsiri iliyoidhinishwa na DMI.',
    proposedOnly: 'Nimepata uhusiano wa maneno uliopendekezwa kwa “{term}”, lakini hakuna tafsiri ya {language} iliyokaguliwa. DMI haijathibitisha maneno hayo.',
    verifiedTranslation: 'Tafsiri ya {language} iliyokaguliwa ya “{term}”: “{translation}”.',
  },
} satisfies Record<ChatLanguage, Record<string, string | string[]>>;
