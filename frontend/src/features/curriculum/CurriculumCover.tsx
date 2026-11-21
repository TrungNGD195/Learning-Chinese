import {curriculumCoverAtlas,type CoverTopic} from './curriculumCoverData'

export function CurriculumCover({topic}:{topic:CoverTopic}){
 const {src,size,position,label}=curriculumCoverAtlas(topic)
 return <span className="lc-painted-cover" role="img" aria-label={label} data-cover-topic={topic} style={{backgroundImage:`url('${src}')`,backgroundSize:size,backgroundPosition:position}}/>
}
