import {topics,type CoverTopic} from './curriculumCoverData'

export function CurriculumCover({topic}:{topic:CoverTopic}){
 const [cell,label]=topics[topic]
 return <span className="lc-painted-cover" role="img" aria-label={label} data-cover-topic={topic} style={{backgroundImage:"url('/academy/curriculum-v2/covers.png')",backgroundSize:'300% 300%',backgroundPosition:`${cell%3*50}% ${Math.floor(cell/3)*50}%`}}/>
}
